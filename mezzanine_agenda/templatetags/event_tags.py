# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.sites.models import Site
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.http import urlquote as quote
from django.utils.safestring import mark_safe

from mezzanine_agenda.models import Event, EventLocation
from mezzanine.conf import settings
from mezzanine.generic.models import Keyword
from mezzanine.template import Library
from mezzanine.utils.models import get_user_model
from mezzanine.utils.sites import current_site_id
from mezzanine_agenda.utils import sign_url

import pytz

from time import strptime
from datetime import datetime, timedelta

from mezzanine_agenda.views import week_day_range
User = get_user_model()

register = Library()


@register.as_tag
def event_months(*args):
    """
    Put a list of dates for events into the template context.
    """
    if settings.EVENT_TIME_ZONE != "":
        app_timezone = pytz.timezone(settings.EVENT_TIME_ZONE)
    else:
        app_timezone = timezone.get_default_timezone()
    dates = Event.objects.published().values_list("start", flat=True)
    correct_timezone_dates = [timezone.make_naive(date, app_timezone) for date in dates]
    date_dicts = [
        {"date": datetime(date.year, date.month, 1)} for date in correct_timezone_dates
    ]
    month_dicts = []
    for date_dict in date_dicts:
        if date_dict not in month_dicts:
            month_dicts.append(date_dict)
    for i, date_dict in enumerate(month_dicts):
        month_dicts[i]["event_count"] = date_dicts.count(date_dict)
    return month_dicts


@register.as_tag
def event_locations(*args):
    """
    Put a list of locations for events into the template context.
    """
    events = Event.objects.published()
    locations = EventLocation.objects.filter(event__in=events)
    return list(locations.annotate(event_count=Count("event")))


@register.as_tag
def event_authors(*args):
    """
    Put a list of authors (users) for events into the template context.
    """
    events = Event.objects.published()
    authors = User.objects.filter(events__in=events)
    return list(authors.annotate(event_count=Count("events")))


@register.as_tag
def recent_events(limit=5, tag=None, username=None, location=None):
    """
    Put a list of recent events into the template
    context. A tag title or slug, location title or slug or author's
    username can also be specified to filter the recent events returned.

    Usage::

        {% recent_events 5 as recent_events %}
        {% recent_events limit=5 tag="django" as recent_events %}
        {% recent_events limit=5 location="home" as recent_events %}
        {% recent_events 5 username=admin as recent_pevents %}

    """
    events = Event.objects.published().select_related("user").order_by('-start')
    events = events.filter(end__lt=datetime.now())
    title_or_slug = lambda s: Q(title=s) | Q(slug=s)  # noqa: E731
    if tag is not None:
        try:
            tag = Keyword.objects.get(title_or_slug(tag))
            events = events.filter(keywords__keyword=tag)
        except Keyword.DoesNotExist:
            return []
    if location is not None:
        try:
            location = EventLocation.objects.get(title_or_slug(location))
            events = events.filter(location=location)
        except EventLocation.DoesNotExist:
            return []
    if username is not None:
        try:
            author = User.objects.get(username=username)
            events = events.filter(user=author)
        except User.DoesNotExist:
            return []
    return list(events[:limit])


@register.as_tag
def upcoming_events(limit=5, tag=None, username=None, location=None):
    """
    Put a list of upcoming events into the template
    context. A tag title or slug, location title or slug or author's
    username can also be specified to filter the upcoming events returned.

    Usage::

        {% upcoming_events 5 as upcoming_events %}
        {% upcoming_events limit=5 tag="django" as upcoming_events %}
        {% upcoming_events limit=5 location="home" as upcoming_events %}
        {% upcoming_events 5 username=admin as upcoming_events %}

    """
    events = Event.objects.published().select_related("user").order_by('start')
    # Get upcoming events/ongoing events
    events = events.filter(Q(start__gt=datetime.now()) | Q(end__gt=datetime.now()))
    title_or_slug = lambda s: Q(title=s) | Q(slug=s)  # noqa: E731
    if tag is not None:
        try:
            tag = Keyword.objects.get(title_or_slug(tag))
            events = events.filter(keywords__keyword=tag)
        except Keyword.DoesNotExist:
            return []
    if location is not None:
        try:
            location = EventLocation.objects.get(title_or_slug(location))
            events = events.filter(location=location)
        except EventLocation.DoesNotExist:
            return []
    if username is not None:
        try:
            author = User.objects.get(username=username)
            events = events.filter(user=author)
        except User.DoesNotExist:
            return []
    return list(events[:limit])


def _get_utc(datetime):
    """
    Convert datetime object to be timezone aware and in UTC.
    """
    if settings.EVENT_TIME_ZONE != "":
        app_timezone = pytz.timezone(settings.EVENT_TIME_ZONE)
    else:
        app_timezone = timezone.get_default_timezone()

    # make the datetime aware
    if timezone.is_naive(datetime):
        datetime = timezone.make_aware(datetime, app_timezone)

    # now, make it UTC
    datetime = timezone.make_naive(datetime, timezone.utc)

    return datetime


@register.filter(is_safe=True)
def google_calendar_url(event):
    """
    Generates a link to add the event to your google calendar.
    """
    if not isinstance(event, Event):
        return ''
    title = quote(event.title)
    start_date = _get_utc(event.start).strftime("%Y%m%dT%H%M%SZ")
    if event.end:
        end_date = _get_utc(event.end).strftime("%Y%m%dT%H%M%SZ")
    else:
        end_date = start_date
    url = Site.objects.get(id=current_site_id()).domain + event.get_absolute_url()
    if event.location and event.location.mappable_location:
        location = quote(event.location.mappable_location)
    else:
        location = None
    return "http://www.google.com/calendar/event?action=TEMPLATE&text={title}&dates={start_date}/{end_date}&sprop=website:{url}&location={location}&trp=true".format(**locals())  # noqa: E501


@register.filter(is_safe=True)
def google_nav_url(obj):
    """
    Generates a link to get directions to an event or location with google maps.
    """
    if isinstance(obj, Event) and obj.location and obj.location.mappable_location:
        location = quote(obj.location.mappable_location)
    elif isinstance(obj, EventLocation) and \
            obj.location and \
            obj.location.mappable_location:
        location = quote(obj.mappable_location)
    else:
        return ''
    return "https://{}/maps/search/?api=1&query={}&key={}".format(
        settings.EVENT_GOOGLE_MAPS_DOMAIN,
        location,
        settings.GOOGLE_API_KEY
    )


@register.simple_tag
def google_static_map(obj, width, height, zoom):
    """
    Generates a static google map for the event location.
    """
    if isinstance(obj, Event) and obj.location and obj.location.mappable_location:
        location = quote(obj.location.mappable_location)
        marker = quote('{:.6},{:.6}'.format(obj.location.lat, obj.location.lon))
    elif isinstance(obj, EventLocation) and \
            obj.location and \
            obj.location.mappable_location:
        location = quote(obj.mappable_location)
        marker = quote('{:.6},{:.6}'.format(obj.lat, obj.lon))
    else:
        return ''
    if settings.EVENT_HIDPI_STATIC_MAPS:
        scale = 2
    else:
        scale = 1
    key = settings.GOOGLE_API_KEY
    url = "https://maps.googleapis.com/maps/api/staticmap?size={width}x{height}&scale={scale}&format=png&markers={marker}&sensor=false&zoom={zoom}&key={key}".format(**locals()).encode('utf-8')  # noqa: E501
    url = sign_url(input_url=url, secret=settings.GOOGLE_STATIC_MAPS_API_SECRET)
    if hasattr(settings, "GOOGLE_API_KEY"):
        key = settings.GOOGLE_API_KEY
        url += "&key={key}"
    url = url.format(**locals()).encode('utf-8')
    if hasattr(settings, "GOOGLE_STATIC_MAPS_API_SECRET"):
        url = sign_url(input_url=url, secret=settings.GOOGLE_STATIC_MAPS_API_SECRET)

    return mark_safe(
        "<img src='{url}' width='{width}' height='{height}' />".format(**locals())
    )


@register.simple_tag(takes_context=True)
def icalendar_url(context):
    """
    Generates the link to the icalendar view for the current page.
    """
    if context.get("event"):
        return "%sevent.ics" % context["event"].get_absolute_url()
    else:
        if context.get("tag"):
            return reverse("icalendar_tag", args=(context["tag"],))
        elif context.get("year") and context.get("month"):
            return reverse(
                "icalendar_month",
                args=(
                    context["year"],
                    strptime(context["month"], '%B').tm_mon
                )
            )
        elif context.get("year"):
            return reverse("icalendar_year", args=(context["year"],))
        elif context.get("location"):
            return reverse("icalendar_location", args=(context["location"].slug,))
        elif context.get("author"):
            return reverse("icalendar_author", args=(context["author"],))
        else:
            return reverse("icalendar")


@register.as_tag
def all_events(*args):
    return Event.objects.all()


def perdelta(start, end, delta):
    curr = start
    while curr < end:
        yield curr
        curr += delta


@register.as_tag
def all_days(*args):
    events = Event.objects.all().order_by('start')
    if events:
        lower = events[0].start
        higher = events.latest('start').start
        date_list = [d for d in perdelta(lower, higher, timedelta(days=1))]
        return date_list
    return []


@register.filter
def events_in_day(date):
    return Event.objects.filter(start__date=date)


@register.as_tag
def all_weeks(*args):
    events = Event.objects.all()
    first_event = events[0]
    last_event = events[len(events)-1]
    return range(
        first_event.start.isocalendar()[1], last_event.start.isocalendar()[1]+1
    )


@register.filter
def week_range(week, year):
    return week_day_range(year, week)


@register.filter
def subtract(value, arg):
    return value - arg


@register.filter
def same_time_in_periods(periods):
    is_same_time = True
    if periods:
        last_time_from = periods[0].date_from.time()
        last_time_to = None
        if periods[0].date_to:
            last_time_to = periods[0].date_to.time()
        for period in periods:
            if period.date_from:
                if period.date_from.time() != last_time_from:
                    is_same_time = False
            if last_time_to and period.date_to:
                if period.date_to.time() != last_time_to:
                    is_same_time = False

    return is_same_time


@register.filter
def same_day_in_periods(periods):
    is_same_day = True
    if len(periods) >= 2:
        first_period = periods[0]
        for period in periods:
            if first_period.date_from.date != period.date_from.date:
                is_same_day = False
    return is_same_day


@register.filter
def tag_is_excluded(tag_id):
    return tag_id in settings.EVENT_EXCLUDE_TAG_LIST


@register.filter
def get_tag(tag_id):
    return Keyword.objects.get(id=tag_id)
