from __future__ import unicode_literals

from django.conf.urls import url

from mezzanine.conf import settings
from mezzanine_agenda.views import event_feed, EventListView, icalendar,\
    ArchiveListView, event_detail, icalendar_event, event_booking,\
    EventBookingShopConfirmationView, EventBookingGlobalConfirmationView,\
    EventBookingPassView, LocationListView, LocationDetailView,\
    EventPriceAutocompleteView

# Trailing slash for urlpatterns based on setup.
_slash = "/" if settings.APPEND_SLASH else ""


# Agenda patterns.
urlpatterns = [
    url("^feeds/(?P<format>.*)%s$" % _slash,
        event_feed, name="event_feed"),
    url("^tag/(?P<tag>.*)/feeds/(?P<format>.*)%s$" % _slash,
        event_feed, name="event_feed_tag"),
    url(r"^tag/(?P<tag>[-a-zA-Z0-9]*)[%s]?$" % _slash, EventListView.as_view(),
        name="event_list_tag"),
    url(r"^/tag/(?P<tag>[-a-zA-Z0-9]*)[%s]?$" % _slash, EventListView.as_view(),
        name="event_list_tag"),
    url("^tag/(?P<tag>.*)/calendar.ics$", icalendar,
        name="icalendar_tag"),
    url("^location/(?P<location>.*)/feeds/(?P<format>.*)%s$" % _slash,
        event_feed, name="event_feed_location"),
    url("^location/(?P<location>.*)[%s]?$" % _slash,
        EventListView.as_view(), name="event_list_location"),
    url("^location/(?P<location>.*)/calendar.ics$",
        icalendar, name="icalendar_location"),
    url("^author/(?P<username>.*)/feeds/(?P<format>.*)%s$" % _slash,
        event_feed, name="event_feed_author"),
    url("^author/(?P<username>.*)[%s]?$" % _slash,
        EventListView.as_view(), name="event_list_author"),
    url("^author/(?P<username>.*)/calendar.ics$",
        icalendar, name="icalendar_author"),
    url(r"^archive/(?P<year>\d{4})/(?P<month>\d{1,2})[%s]?$" % _slash,
        ArchiveListView.as_view(), name="event_list_month"),
    url(r"^archive/(?P<year>\d{4})/(?P<month>\d{1,2})/calendar.ics$",
        icalendar, name="icalendar_month"),
    url(r'^archive(?:/(?P<year>\d{4}))?[%s]?$' % _slash,
        ArchiveListView.as_view(), name="event_list_year"),
    url(r"^archive/(?P<year>\d{4})/calendar.ics$",
        icalendar, name="icalendar_year"),
    url(r"^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/"
        "(?P<slug>.*)%s$" % _slash,
        event_detail, name="event_detail_day"),
    url(r"^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<slug>.*)%s$" % _slash,
        event_detail, name="event_detail_month"),
    url(r"^(?P<year>\d{4})/(?P<slug>.*)%s$" % _slash,
        event_detail, name="event_detail_year"),
    url(r"^week/(?P<year>\d{4})/(?P<week>\d{1,2})[%s]?$" % _slash,
        EventListView.as_view(), name="event_list_week"),
    url(r"^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/"
        "(?P<slug>.*)/event.ics$", icalendar_event, name="icalendar_event_day"),
    url(r"^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<slug>.*)/event.ics$",
        icalendar_event, name="icalendar_event_month"),
    url(r"^(?P<year>\d{4})/(?P<slug>.*)/event.ics$",
        icalendar_event, name="icalendar_event_year"),
    url("^(?P<slug>.*)/detail/event.ics$", icalendar_event, name="icalendar_event"),
    url("^calendar.ics$", icalendar, name="icalendar"),
    url(
        "^(?P<slug>.*)/detail[%s]?$" % _slash, event_detail,
        name="event_detail"
    ),
    url(
        "^/(?P<slug>.*)/detail[%s]?$" % _slash, event_detail,
        name="event_detail"
    ),
    url("^$", EventListView.as_view(), name="event_list"),
    url("^(?P<slug>.*)/booking%s$" % _slash, event_booking,
        name="event_booking"),
    url(
        "^shop/(?P<pk>.*)/confirmation%s$" % _slash,
        EventBookingShopConfirmationView.as_view(),
        name="event_booking_shop_confirmation"
    ),
    url(
        "^confirmation/(?P<transaction_id>[0-9]*)$",
        EventBookingGlobalConfirmationView.as_view(),
        name="event_booking_global_confirmation"
    ),
    url(
        "^pass%s$" % _slash,
        EventBookingPassView.as_view(),
        name="event_pass"
    ),
    url(
        r"^archive/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})%s$" % _slash,
        ArchiveListView.as_view(), name="event_list_day"
    ),
    url("^locations/$", LocationListView.as_view(), name="location-list"),
    url("^locations/(?P<slug>.*)%s$" % _slash,
        LocationDetailView.as_view(), name="location-detail"),
    url("^event-price-autocomplete$",
        EventPriceAutocompleteView.as_view(), name="event-price-autocomplete"),
]
