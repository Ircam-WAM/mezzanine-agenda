from __future__ import unicode_literals
from future.builtins import str
from future.builtins import int
from calendar import month_name, monthrange
from datetime import datetime, date, timedelta, time

from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.views.generic.base import TemplateView
from django.core import serializers
from icalendar import Calendar
from dal import autocomplete

from mezzanine_agenda import __version__
from mezzanine_agenda.models import Event, EventLocation,\
    ExternalShop, Season, EventPrice
from mezzanine_agenda.feeds import EventsRSS, EventsAtom
from mezzanine.conf import settings
from mezzanine.generic.models import Keyword
from mezzanine.utils.views import render
from mezzanine.utils.models import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify
from django.utils import translation

from mezzanine_agenda.forms import EventFilterForm

User = get_user_model()

MONTH_CHOICES = {
    1: _('January'),
    2: _('February'),
    3: _('March'),
    4: _('April'),
    5: _('May'),
    6: _('June'),
    7: _('July'),
    8: _('August'),
    9: _('September'),
    10: _('October'),
    11: _('November'),
    12: _('December'),
}


def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + timedelta(days_ahead)


def week_day_range(year, week):
    first_day = date(int(year), 1, 1)
    lower_date = next_weekday(first_day, 0) + timedelta(weeks=int(week)-1)
    higher_date = lower_date + timedelta(days=int(6))
    return lower_date, higher_date


class EventListView(ListView):
    """
    Display a list of events that are filtered by tag, year, month, week,
    author or location. Custom templates are checked for using the name
    ``agenda/event_list_XXX.html`` where ``XXX`` is either the
    location slug or author's username if given.
    """
    model = Event
    template_name = "agenda/event_list.html"
    context_object_name = 'events'
    form_initial = {}

    def get(self, request, *args, **kwargs):
        response = super(EventListView, self).get(request, *args, **kwargs)
        # AJAX
        if request.is_ajax():
            object_list_json = serializers.serialize('json', self.object_list)
            response = JsonResponse(object_list_json, safe=False)
        return response

    def get_queryset(self, tag=None):
        self.templates = []
        self.day_date = None
        events = None
        self.tag = None if "tag" not in self.kwargs else self.kwargs['tag']
        self.year = None if "year" not in self.kwargs else self.kwargs['year']
        self.month = None if "month" not in self.kwargs else self.kwargs['month']
        self.day = None if "day" not in self.kwargs else self.kwargs['day']
        self.username = None if "username" not in self.kwargs else self.kwargs[
            'username'
        ]
        self.location = None if "location" not in self.kwargs else self.kwargs[
            'location'
        ]
        self.week = None if "week" not in self.kwargs else self.kwargs['week']

        # display all events if user belongs to the staff
        if self.request.user.is_staff:
            events = Event.objects.all()
        else:
            events = Event.objects.published(for_user=self.request.user)

        # if not day:
        #     events = events.filter(parent=None)
        if self.year is not None:
            events = events.filter(start__year=self.year)
            if self.month is not None:
                events = events.filter(start__month=self.month)
                try:
                    month_orig = self.month
                    self.month = month_name[int(self.month)]
                except IndexError:
                    raise Http404()
                if self.day is not None:
                    events = events.filter(start__day=self.day)
                    self.day_date = date(
                        year=int(self.year),
                        month=int(month_orig),
                        day=int(self.day)
                    )
            elif self.week is not None:
                events = events.filter(start__year=self.year)
                lower_date, higher_date = week_day_range(self.year, self.week)
                events = events.filter(start__range=(lower_date, higher_date))
        if self.location is not None:
            self.location = get_object_or_404(EventLocation, slug=self.location)
            events = events.filter(location=self.location)
            self.templates.append(
                u"agenda/event_list_%s.html" %
                str(self.location.slug)
            )
        self.author = None
        if self.username is not None:
            self.author = get_object_or_404(User, username=self.username)
            events = events.filter(user=self.author)
            self.templates.append(u"agenda/event_list_%s.html" % self.username)

        if not self.year and not self.location and not self.username:
            # Get upcoming events/ongoing events
            events = events.filter(
                Q(start__gt=datetime.now()) | Q(end__gt=datetime.now())
            )

        # Filter by locations
        event_locations_filter = self.request.GET.getlist('event_locations_filter')
        if event_locations_filter:
            events = events.filter(location__title__in=event_locations_filter)
            self.form_initial['event_locations_filter'] = event_locations_filter

        # Filter by categories
        event_categories_filter = self.request.GET.getlist('event_categories_filter')
        if event_categories_filter:
            events = events.filter(category__name__in=event_categories_filter)
            self.form_initial['event_categories_filter'] = event_categories_filter

        prefetch = ("keywords__keyword",)
        events = events.select_related("user").prefetch_related(*prefetch)
        self.templates.append(self.template_name)

        self.tag_list = events.values_list(
            'keywords__keyword',
            flat=True,
        )
        self.tag_list = list(dict.fromkeys(self.tag_list))
        removed = []
        for tag in self.tag_list:
            if tag is None or tag in settings.EVENT_EXCLUDE_TAG_LIST:
                removed.append(tag)
        for tag in removed:
            self.tag_list.remove(tag)
        self.tag_list = Keyword.objects.filter(id__in=self.tag_list)

        if self.tag is not None:
            self.tag = get_object_or_404(Keyword, slug=self.tag)
            events = events.filter(keywords__keyword=self.tag)
        else:
            for exclude_tag_id in settings.EVENT_EXCLUDE_TAG_LIST:
                exclude_tag = get_object_or_404(Keyword, id=exclude_tag_id)
                events = events.exclude(keywords__keyword=exclude_tag)

        months = events.order_by(
            "start"
        ).values_list(
            'start__month',
            'start__year'
        )
        months = list(dict.fromkeys(months))

        if months:
            already = []
            events_by_month = {}
            for month, year in months:
                with translation.override('fr'):
                    m = str(MONTH_CHOICES[month])
                events_by_month[
                    m +
                    ' ' +
                    str(year) +
                    ',' +
                    MONTH_CHOICES[month] +
                    ' ' +
                    str(year)
                ] = []
                digit_month = int(month)
                first_day_in_month = date(year, digit_month, 1)
                last_day_in_month = date(
                    year, digit_month,
                    monthrange(year, digit_month)[1]
                )
                tmp = events\
                    .filter(
                        start__year=year,
                    )\
                    .filter(
                        (
                            Q(start__lt=first_day_in_month,)
                            & Q(end__gt=last_day_in_month)
                        )
                        | Q(start__range=(first_day_in_month, last_day_in_month))
                        | Q(start__month=month)
                    ).order_by("start")
                for event in tmp:
                    if event.id not in already:
                        with translation.override('fr'):
                            m = str(MONTH_CHOICES[month])
                        events_by_month[
                            m +
                            ' ' +
                            str(year) +
                            ',' +
                            MONTH_CHOICES[month] +
                            ' ' +
                            str(year)
                        ].append(event)
                        already.append(event.id)
            return events_by_month  # events in template context

        return events

    def get_context_data(self, *args, **kwargs):
        tmp = self.request.page
        root = self.request.page
        while tmp:
            if tmp.parent:
                tmp = tmp.parent
            else:
                root = tmp
                tmp = False
        menu = [root]
        if root == self.request.page:
            submenu = []
            for month in self.object_list:
                m = month.split(',')
                submenu.append({
                    "href": slugify(m[0]),
                    "text": m[1],
                    "extra_class": "slow-move"
                })
            menu.append(submenu)

        for page in root.children.all().order_by("_order"):
            menu.append(page)
            if page == self.request.page:
                submenu = []
                for month in self.object_list:
                    m = month.split(',')
                    submenu.append({
                        "href": slugify(m[0]),
                        "text": m[1],
                        "extra_class": "slow-move"
                    })
                menu.append(submenu)

        context = super(EventListView, self).get_context_data(**kwargs)
        context.update(
            {
                "year": self.year,
                "month": self.month,
                "day": self.day,
                "week": self.week,
                "tag_list": self.tag_list,
                "tag": self.tag,
                "location": self.location,
                "author": self.author,
                'day_date': self.day_date,
                'is_archive': False,
                'ordered_by_month': True,
                'menu': menu
            }
        )

        context['event_tag_highlighted'] = getattr(settings, 'EVENT_TAG_HIGHLIGHTED', 0)
        context['filter_form'] = EventFilterForm(initial=self.form_initial)
        if settings.PAST_EVENTS:
            context['past_events'] = Event.objects.filter(
                end__lt=datetime.now()
            ).order_by("-start")

        return context


class ArchiveListView(ListView):
    """
    Display a list of events that are filtered by, year, month, day.
    Custom templates are checked for using the name
    ``agenda/event_list_XXX.html`` where ``XXX`` is either the
    location slug or author's username if given.
    """
    model = Event
    template_name = "agenda/event_list.html"
    context_object_name = 'events'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if not hasattr(self.kwargs, 'year'):
            self.kwargs['year'] = None
        if self.kwargs['year'] is None:
            curr_year = date.today().year
            response = redirect('event_list_year', year=curr_year)
        return response

    def get_queryset(self, tag=None):

        self.templates = self.template_name
        self.day_date = None
        events = None
        date_now = datetime.now()
        self.year = date_now.year if (
            "year" not in self.kwargs or self.kwargs['year'] is None
        ) else self.kwargs['year']
        self.month = None if "month" not in self.kwargs else self.kwargs['month']
        self.day = None if "day" not in self.kwargs else self.kwargs['day']
        digit_year = int(self.year)
        events = Event.objects.published(for_user=self.request.user)
        if self.year is not None:
            # we suppose that self.year corresponds to start year of a season
            season, created = Season.objects.get_or_create(
                start__year=digit_year,
                defaults={
                    'title': 'Season ' + str(self.year) + '-' + str(digit_year + 1),
                    'start': date(digit_year, 7, 31),
                    'end': date(digit_year + 1, 8, 1)
                }
            )

            # filter events from beginning of seasons to today or end of season
            if date_now.date() > season.end:
                date_max = datetime.combine(season.end, time(23, 59, 59))
            else:
                date_max = date_now
            season.start = datetime.combine(season.start, time(0, 0, 0))
            events = events.filter(
                Q(start__range=[season.start, date_max]) &
                Q(end__range=[season.start, date_max])
            ).order_by("-start")

            # filter by month
            if self.month is not None:
                digit_month = int(self.month)
                first_day_in_month = date(digit_year, digit_month, 1)
                last_day_in_month = date(
                    digit_year, digit_month,
                    monthrange(digit_year, digit_month)[1]
                )
                # works for periods containing the month or a period in the month
                events = events.filter(
                    (
                        Q(start__lt=first_day_in_month)
                        & Q(end__gt=last_day_in_month)
                    )
                    | Q(start__range=(first_day_in_month, last_day_in_month))
                    | Q(end__month=self.month)
                    | Q(start__month=self.month)
                ).order_by("start")
                try:
                    month_orig = self.month
                    self.month = month_name[int(self.month)]
                except IndexError:
                    raise Http404()
                if self.day is not None:
                    events = events.filter(start__day=self.day)
                    self.day_date = date(
                        year=digit_year,
                        month=int(month_orig),
                        day=int(self.day)
                    )
        months = events.order_by(
            "-start"
        ).values_list(
            'start__month',
            'start__year'
        )
        months = list(dict.fromkeys(months))
        if months:
            already = []
            events_by_month = {}
            for month, year in months:

                with translation.override('fr'):
                    m = str(MONTH_CHOICES[month])
                events_by_month[
                    m +
                    ' ' +
                    str(year) +
                    ',' +
                    MONTH_CHOICES[month] +
                    ' ' +
                    str(year)
                ] = []
                digit_month = int(month)
                first_day_in_month = date(digit_year, digit_month, 1)
                last_day_in_month = date(
                    digit_year, digit_month,
                    monthrange(digit_year, digit_month)[1]
                )
                tmp = events\
                    .filter(
                        start__year=year,
                    )\
                    .filter(
                        (
                            Q(start__lt=first_day_in_month,)
                            & Q(end__gt=last_day_in_month)
                        )
                        | Q(start__range=(first_day_in_month, last_day_in_month))
                        | Q(start__month=month)
                    ).order_by("-start")
                for event in tmp:
                    if event.id not in already:
                        with translation.override('fr'):
                            m = str(MONTH_CHOICES[month])
                        events_by_month[
                            m +
                            ' ' +
                            str(year) +
                            ',' +
                            MONTH_CHOICES[month] +
                            ' ' +
                            str(year)
                        ].append(event)
                        already.append(event.id)
            return events_by_month  # events in template context
        return events

    def get_context_data(self, *args, **kwargs):
        tmp = self.request.page
        root = self.request.page
        while tmp:
            if tmp.parent:
                tmp = tmp.parent
            else:
                root = tmp
                tmp = False
        menu = [root]
        for page in root.children.all().order_by("_order"):
            menu.append(page)
            submenu = []
            for page2 in page.children.all().order_by("_order"):
                submenu.append(page2)
                if page2 == self.request.page:
                    subsubmenu = []
                    for month in self.object_list:
                        m = month.split(',')
                        subsubmenu.append({
                            "href": slugify(m[0]),
                            "text": m[1],
                            "extra_class": "slow-move"
                        })
                    submenu.append(subsubmenu)
            menu.append(submenu)
        context = super(ArchiveListView, self).get_context_data(**kwargs)
        context.update(
            {
                "year": self.year,
                "month": self.month,
                "day": self.day,
                'day_date': self.day_date,
                'is_archive': True,
                'menu': menu,
                'ordered_by_month': True
            }
        )
        return context


def event_detail(
    request,
    slug,
    year=None,
    month=None,
    day=None,
    template="agenda/event_detail.html"
):
    """. Custom templates are checked for using the name
    ``agenda/event_detail_XXX.html`` where ``XXX`` is the agenda
    events's slug.
    """
    events = Event.objects.published(for_user=request.user).select_related()
    event = get_object_or_404(events, slug=slug)
    context = {"event": event, }
    templates = [u"agenda/event_detail_%s.html" % str(slug), template]
    return render(request, templates, context)


def event_booking(
    request,
    slug,
    year=None,
    month=None,
    day=None,
    template="agenda/event_booking.html"
):
    """. Custom templates are checked for using the name
    ``agenda/event_detail_XXX.html`` where ``XXX`` is the agenda
    events's slug.
    """
    events = Event.objects.published(
                                     for_user=request.user).select_related()
    event = get_object_or_404(events, slug=slug)
    if event.is_full:
        return redirect('event_detail', slug=event.slug)
    shop_url = ''
    if event.external_id:
        if event.shop:
            shop_url = event.shop.item_url % event.external_id
        else:
            shop_url = settings.EVENT_SHOP_URL % event.external_id
    context = {
        "event": event,
        "editable_obj": event,
        "shop_url": shop_url,
        'external_id': event.external_id
    }
    templates = [u"agenda/event_detail_%s.html" % str(slug), template]
    return render(request, templates, context)


def event_feed(request, format, **kwargs):
    """
    Events feeds - maps format to the correct feed view.
    """
    try:
        return {"rss": EventsRSS, "atom": EventsAtom}[format](**kwargs)(request)
    except KeyError:
        raise Http404()


def _make_icalendar():
    """
    Create an icalendar object.
    """
    icalendar = Calendar()
    icalendar.add(
        'prodid',
        '-//mezzanine-agenda//NONSGML V{}//EN'.format(__version__)
    )
    icalendar.add('version', '2.0')  # version of the format, not the product!
    return icalendar


def icalendar_event(request, slug, year=None, month=None, day=None):
    """
    Returns the icalendar for a specific event.
    """
    events = Event.objects.published(
                                     for_user=request.user).select_related()
    event = get_object_or_404(events, slug=slug)

    icalendar = _make_icalendar()
    icalendar_event = event.get_icalendar_event()
    icalendar.add_component(icalendar_event)

    return HttpResponse(icalendar.to_ical(), content_type="text/calendar")


def icalendar(
    request,
    tag=None,
    year=None,
    month=None,
    username=None,
    location=None
):
    """
    Returns the icalendar for a group of events that are filtered by tag,
    year, month, author or location.
    """
    events = Event.objects.published(for_user=request.user)
    if tag is not None:
        tag = get_object_or_404(Keyword, slug=tag)
        events = events.filter(keywords__keyword=tag)
    if year is not None:
        events = events.filter(start__year=year)
        if month is not None:
            events = events.filter(start__month=month)
            try:
                month = month_name[int(month)]
            except IndexError:
                raise Http404()
    if location is not None:
        location = get_object_or_404(EventLocation, slug=location)
        events = events.filter(location=location)
    author = None
    if username is not None:
        author = get_object_or_404(User, username=username)
        events = events.filter(user=author)
    if not tag and not year and not location and not username:
        # Get upcoming events/ongoing events
        events = events.filter(
            Q(start__gt=datetime.now()) |
            Q(end__gt=datetime.now())
        ).order_by("start")

    prefetch = ("keywords__keyword",)
    events = events.select_related("user").prefetch_related(*prefetch)

    icalendar = _make_icalendar()
    for event in events:
        icalendar_event = event.get_icalendar_event()
        icalendar.add_component(icalendar_event)

    return HttpResponse(icalendar.to_ical(), content_type="text/calendar")


class LocationListView(ListView):

    model = EventLocation
    template_name = 'agenda/event_location_list.html'

    def get_queryset(self):
        location_list = []
        room = []
        locations = self.model.objects.all().order_by('room')
        for location in locations:
            if location.room:
                if location.room not in room:
                    location_list.append(location)
                    room.append(location.room)
            else:
                location_list.append(location)
        return location_list

    def get_context_data(self, **kwargs):
        context = super(LocationListView, self).get_context_data(**kwargs)
        return context


class LocationDetailView(DetailView):

    model = EventLocation
    template_name = 'agenda/event_location_detail.html'
    context_object_name = 'location'

    def get_context_data(self, **kwargs):
        context = super(LocationDetailView, self).get_context_data(**kwargs)
        return context


class EventBookingPassView(TemplateView):

    template_name = 'agenda/event_iframe.html'

    def get_context_data(self, **kwargs):
        context = super(EventBookingPassView, self).get_context_data(**kwargs)
        context['url'] = settings.EVENT_PASS_URL
        context['title'] = 'Pass'
        return context


class EventBookingGlobalConfirmationView(TemplateView):

    template_name = "agenda/event_booking_confirmation.html"

    def get_context_data(self, **kwargs):
        context = super(
            EventBookingGlobalConfirmationView,
            self
        ).get_context_data(**kwargs)
        context['confirmation_url'] = settings.EVENT_CONFIRMATION_URL %\
            kwargs['transaction_id']
        return context


class EventBookingShopConfirmationView(DetailView):

    model = ExternalShop
    template_name = "agenda/event_booking_confirmation.html"

    def get_context_data(self, **kwargs):
        context = super(
            EventBookingShopConfirmationView,
            self
        ).get_context_data(**kwargs)
        context['confirmation_url'] = self.get_object().confirmation_url
        return context


class EventPriceAutocompleteView(autocomplete.Select2QuerySetView):

    def get_result_label(self, item):
        desc = ""
        if hasattr(item, "event_price_description"):
            desc = ' - ' + item.event_price_description.description
        return str(item.value) + item.unit + desc

    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return EventPrice.objects.none()

        qs = EventPrice.objects.all()

        value = self.forwarded.get('value', None)

        if value:
            qs = qs.filter(value=value)

        if self.q:
            qs = qs.filter(value__istartswith=self.q)

        return qs
