from __future__ import unicode_literals
from future.builtins import str

from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from geopy.geocoders import GoogleV3 as GoogleMaps
from geopy.exc import GeocoderQueryError

from icalendar import Event as IEvent
from copy import deepcopy

from mezzanine.conf import settings
from mezzanine.core.fields import FileField, RichTextField, OrderField
from mezzanine.core.models import Displayable, TeamOwnable, RichText, Slugged, SiteRelated
from mezzanine.generic.fields import CommentsField, RatingField
from mezzanine.utils.models import AdminThumbMixin, upload_to
from mezzanine.utils.sites import current_site_id
from mezzanine.utils.models import base_concrete_model, get_user_model_name

from organization.core.models import TitledSlugged


ALIGNMENT_CHOICES = (('left', _('left')), ('center', _('center')), ('right', _('right')))


class SubTitle(models.Model):

    sub_title = models.TextField(_('sub title'), blank=True, max_length=1024)

    class Meta:
        abstract = True


class Event(Displayable, SubTitle, TeamOwnable, RichText, AdminThumbMixin):
    """
    An event.
    """
    search_fields = {"title": 50, "content": 25}
    parent = models.ForeignKey('Event', verbose_name=_('parent'), related_name='children', blank=True, null=True, on_delete=models.SET_NULL)
    category = models.ForeignKey('EventCategory', verbose_name=_('category'), related_name='events', blank=True, null=True, on_delete=models.SET_NULL)

    start = models.DateTimeField(_("Start"))
    end = models.DateTimeField(_("End"), blank=True, null=True)
    date_text = models.CharField(_('Date text'), max_length=512, blank=True, null=True)

    location = models.ForeignKey("EventLocation", blank=True, null=True, on_delete=models.SET_NULL)
    facebook_event = models.BigIntegerField(_('Facebook ID'), blank=True, null=True)
    shop = models.ForeignKey('ExternalShop', verbose_name=_('shop'), related_name='events', blank=True, null=True, on_delete=models.SET_NULL)
    external_id = models.IntegerField(_('External ID'), null=True, blank=True)
    is_full = models.BooleanField(verbose_name=_("Is Full"), default=False)

    brochure = FileField(_('brochure'), upload_to='brochures', max_length=1024, blank=True)
    prices = models.ManyToManyField('EventPrice', verbose_name=_('prices'), related_name='events', blank=True)
    no_price_comments = RichTextField(_('Price comments'), blank=True, null=True)
    mentions = models.TextField(_('mentions'), blank=True)

    allow_comments = models.BooleanField(verbose_name=_("Allow comments"), default=False)
    comments = CommentsField(verbose_name=_("Comments"))
    rating = RatingField(verbose_name=_("Rating"))
    rank = models.IntegerField(verbose_name=_('rank'), blank=True, null=True)

    admin_thumb_field = "photo"

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        ordering = ("rank", "start",)
        permissions = TeamOwnable.Meta.permissions

    def clean(self):
        """
        Validate end date is after the start date.
        """
        super(Event, self).clean()

        if self.end and self.start > self.end:
            raise ValidationError("Start must be sooner than end.")

    def save(self, *args, **kwargs):
        super(Event, self).save(*args, **kwargs)
        # take some values from parent
        if not self.parent is None:
            self.title = self.parent.title
            self.user = self.parent.user
            self.status = self.parent.status
            if not self.location:
                self.location = self.parent.location
            if not self.description:
                self.description = self.parent.description
                self.description_en = self.parent.description_en
            if not self.category:
                self.category = self.parent.category
            if not self.mentions:
                self.mentions = self.parent.mentions
                self.mentions_en = self.parent.mentions_en
            parent_images = self.parent.images.select_related('event').all()
            for parent_image in parent_images:
                if not self.images.filter(file=parent_image.file, type=parent_image.type):
                    parent_image.pk = None
                    parent_image.save()
                    parent_image.event = self
                    parent_image.save()
            if not self.user:
                self.user = self.parent.user
            if not self.status:
                self.status = self.parent.status
            if not self.content:
                self.content = self.parent.content
                self.content_en = self.parent.content_en
            if not self.departments.all():
                parent_departments = self.parent.departments.all()
                for parent_department in parent_departments:
                    parent_department.pk = None
                    parent_department.save()
                    parent_department.event = self
                    parent_department.save()
            if not self.links.all():
                all_links = self.parent.links.all()
                for link in all_links:
                    link.pk = None
                    link.save()
                    link.event = self
                    link.save()
        super(Event, self).save(*args, **kwargs)

    def update(self, *args, **kwargs):
        super(Event, self).save(*args, **kwargs)

    def get_absolute_url(self):
        """
        URLs for events can either be just their slug, or prefixed
        with a portion of the post's publish date, controlled by the
        setting ``EVENT_URLS_DATE_FORMAT``, which can contain the value
        ``year``, ``month``, or ``day``. Each of these maps to the name
        of the corresponding urlpattern, and if defined, we loop through
        each of these and build up the kwargs for the correct urlpattern.
        The order which we loop through them is important, since the
        order goes from least granualr (just year) to most granular
        (year/month/day).
        """
        url_name = "event_detail"
        kwargs = {"slug": self.slug}
        date_parts = ("year", "month", "day")
        if settings.EVENT_URLS_DATE_FORMAT in date_parts:
            url_name = "event_detail_%s" % settings.EVENT_URLS_DATE_FORMAT
            for date_part in date_parts:
                date_value = str(getattr(self.publish_date, date_part))
                if len(date_value) == 1:
                    date_value = "0%s" % date_value
                kwargs[date_part] = date_value
                if date_part == settings.EVENT_URLS_DATE_FORMAT:
                    break
        return reverse(url_name, kwargs=kwargs)

    def get_icalendar_event(self):
        """
        Builds an icalendar.event object from event data.
        """
        icalendar_event = IEvent()
        icalendar_event.add('summary'.encode("utf-8"), self.title)
        icalendar_event.add('url', 'http://{domain}{url}'.format(
            domain=Site.objects.get(id=current_site_id()).domain,
            url=self.get_absolute_url(),
        ))
        if self.location:
            icalendar_event.add('location'.encode("utf-8"), self.location.address)
        icalendar_event.add('dtstamp', self.start)
        icalendar_event.add('dtstart', self.start)
        if self.end:
            icalendar_event.add('dtend', self.end)
        icalendar_event['uid'.encode("utf-8")] = "event-{id}@{domain}".format(
            id=self.id,
            domain=Site.objects.get(id=current_site_id()).domain,
        ).encode("utf-8")
        return icalendar_event

    def _get_next_or_previous_by_start_date(self, is_next):
        """
        Retrieves next or previous object by start date. We implement
        our own version instead of Django's so we can hook into the
        published manager and concrete subclasses.
        """
        arg_start = "start__gte" if is_next else "start__lte"
        arg_rank = "rank__gte" if is_next else "rank__lt"
        order_start = "start" if is_next else "-start"
        order_rank = "rank" if is_next else "-rank"
        lookup = {arg_start: self.start, arg_rank: self.rank}
        concrete_model = base_concrete_model(Displayable, self)
        queryset = concrete_model.objects.exclude(id=self.id)

        try:
            queryset = queryset.published()
        except AttributeError:
            pass

        queryset = queryset.filter(**lookup) \
            .filter(parent__isnull=True) \
            .order_by(order_rank, order_start)
        try:
            return queryset[0]
        except IndexError:
            pass

    def get_next_by_start_date(self):
        """
        Retrieves next object by start date.
        """
        return self._get_next_or_previous_by_start_date(True)

    def get_previous_by_start_date(self):
        """
        Retrieves previous object by start date.
        """
        return self._get_next_or_previous_by_start_date(False)

    def date_format(self):
        if self.periods.all():
            return 'D j F'
        else:
            return 'l j F'

    @property
    def has_vel(self):
        return self.links.filter(link_type__slug='vel').count()

    @property
    def vel(self):
        return self.links.filter(link_type__slug='vel').first().url

    @property
    def has_shop(self):
        return self.external_id and self.shop

    @property
    def is_archived(self):
        return self.end and self.end < timezone.now()

    @property
    def is_free(self):
        return self.prices.filter(value=0.0).count()

    @property
    def reserve_button(self):
        button = {}
        if not (self.is_archived or self.is_full):
            if self.is_free:
                button['url'] = self.get_absolute_url()
                button['label'] = _('Free entry')
                button['target'] = "_self"
            elif self.has_shop:
                button['url'] = reverse("event_booking", kwargs={'slug': self.slug})
                button['label'] = _('Reserve')
                button['target'] = "_self"
            elif self.has_vel:
                button['url'] = self.vel
                button['label'] = _('Reserve')
                button['target'] = "_blank"
        return button
            

class EventLocation(TitledSlugged):
    """
    A Event Location.
    """

    address = models.TextField()
    postal_code = models.CharField(_('postal code'), max_length=16)
    city = models.CharField(_('city'), max_length=255)
    mappable_location = models.CharField(max_length=1024, blank=True, help_text="This address will be used to calculate latitude and longitude. Leave blank and set Latitude and Longitude to specify the location yourself, or leave all three blank to auto-fill from the Location field.")
    lat = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True, verbose_name="Latitude", help_text="Calculated automatically if mappable location is set.")
    lon = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True, verbose_name="Longitude", help_text="Calculated automatically if mappable location is set.")
    room = models.CharField(_('room'), max_length=512, blank=True, null=True)
    description = RichTextField(_('description'), blank=True)
    link = models.URLField(max_length=512, blank=True, null=True)
    external_id = models.IntegerField(_('external_id'), null=True, blank=True)

    class Meta:
        verbose_name = _("Event Location")
        verbose_name_plural = _("Event Locations")
        ordering = ("title",)

    def clean(self):
        """
        Validate set/validate mappable_location, longitude and latitude.
        """
        super(EventLocation, self).clean()

        if self.lat and not self.lon:
            raise ValidationError("Longitude required if specifying latitude.")

        if self.lon and not self.lat:
            raise ValidationError("Latitude required if specifying longitude.")

        if not (self.lat and self.lon) and not self.mappable_location:
            self.mappable_location = self.address.replace("\n"," ").replace('\r', ' ') + ", " + self.postal_code + " " + self.city

        if self.mappable_location and not (self.lat and self.lon): #location should always override lat/long if set
            g = GoogleMaps(api_key=settings.GOOGLE_API_KEY,domain=settings.EVENT_GOOGLE_MAPS_DOMAIN)
            try:
                mappable_location, (lat, lon) = g.geocode(self.mappable_location)
            except GeocoderQueryError as e:
                raise ValidationError("The mappable location you specified could not be found on {service}: \"{error}\" Try changing the mappable location, removing any business names, or leaving mappable location blank and using coordinates from getlatlon.com.".format(service="Google Maps", error=e))
            except ValueError as e:
                raise ValidationError("The mappable location you specified could not be found on {service}: \"{error}\" Try changing the mappable location, removing any business names, or leaving mappable location blank and using coordinates from getlatlon.com.".format(service="Google Maps", error=e.message))
            self.mappable_location = mappable_location
            self.lat = lat
            self.lon = lon
            print("self.lat", self.lat)
            print("self.lon", self.lon)
            print("self.mappable_location", self.mappable_location)

    def save(self, *args, **kwargs):
        self.clean()
        super(EventLocation, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.title + " - " + self.room)

    @models.permalink
    def get_absolute_url(self):
        return ("event_list_location", (), {"location": self.slug})


class EventPrice(models.Model):
    """(EventPrice description)"""

    value = models.FloatField(_('value'))
    unit = models.CharField(_('Unit'), max_length=16, blank=True, null=True)

    class Meta:
        verbose_name = _("Event price")
        verbose_name_plural = _("Event prices")
        ordering = ('-value',)

    def __str__(self):
        return str(self.value)


class EventCategory(SiteRelated):

    name = models.CharField(_('name'), max_length=512)
    description = models.TextField(_('description'), blank=True)

    class Meta:
        verbose_name = _("Event category")
        verbose_name_plural = _("Event categories")

    def __str__(self):
        return self.name

    @property
    def slug(self):
        return slugify(self.__unicode__())


class ExternalShop(models.Model):
    
    name = models.CharField(_('name'), max_length=512)
    description = models.TextField(_('description'), blank=True)
    title = models.CharField(_('title'), max_length=512, help_text="Used for display", null=True, blank=True)
    content = RichTextField(_("Content"), blank=True, null=True)
    item_url = models.CharField(_('Item URL'), max_length=255)
    pass_url = models.CharField(_('Pass URL'), max_length=255, blank=True, null=True)
    confirmation_url = models.CharField(_('Confirmation URL'), max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _("External shop")
        verbose_name_plural = _("External shops")

    def __str__(self):
        return self.name


class Season(models.Model):

    title = models.CharField(_('name'), max_length=512)
    start = models.DateField(_('start'))
    end = models.DateField(_('end'))

    def clean(self):
        cleaned_data = super(Season, self).clean()
        queryset = Season.objects.filter(
                    Q(start__startswith=self.start.strftime('%Y'))
                      and Q(end__startswith=self.end.strftime('%Y')))

        if not self.id is None:
            queryset = queryset.exclude(id=self.id)

        if queryset.exists():
            raise ValidationError(_('This season already exists.'))


    class Meta:
        verbose_name = _("Season")
        verbose_name_plural = _("Seasons")


    def __str__(self):
        return self.title
