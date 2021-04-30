# -*- coding: utf-8 -*-
import hashlib
import hmac
import base64
import pandas as pd
from urllib.parse import urlparse
from collections import OrderedDict
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.conf import settings
from mezzanine_agenda.models import Event, EventLocation


date_week = [_('MO'), _('TU'), _('WE'), _('TH'), _('FR'), _('SA'), _('SU')]

def get_events_list_days_form(locations=[]):
    """
    Return HTML choices with specifics specific attributes and css classes
    """
    allEvents = Event.objects.published().order_by('start')

    events_all_date = {}
    events_filtred = {}
    events_by_day = []
    day_dict = OrderedDict()

    # List events date
    for event in allEvents:
        events_all_date[event.start.strftime('%Y-%m-%d')] = event.start
        for period in event.periods.all():
            events_all_date[period.date_from.strftime('%Y-%m-%d')] = period.date_from

    events_filtred = events_all_date

    if locations:
        eventLocations = EventLocation.objects.filter(title__in=locations);
        eventsFiltred = allEvents.filter(location__in=eventLocations)
        # List events date
        if eventsFiltred :
            events_filtred = {}
        for event in eventsFiltred:
            events_filtred[event.start.strftime('%Y-%m-%d')] = event.start
            for period in event.periods.all():
                events_filtred[period.date_from.strftime('%Y-%m-%d')] = period.date_from
    # Create range of days between the earliest and oldest event
    day_list = pd.date_range(start=events_all_date[min(events_all_date)], end=events_all_date[max(events_all_date)], normalize=True).tolist()
    for a_day in day_list :
        day_dict[a_day.strftime('%Y-%m-%d')] = a_day

    # Determine which days
    for day_k, day_v in day_dict.items():
        disabled = ''
        weekend_class = ''
        if not day_k in events_filtred.keys():
            disabled = 'disabled'
        if day_v.dayofweek == 5 or  day_v.dayofweek == 6:
            weekend_class = 'calendar__weekend'
        label = str(day_v.day)
        events_by_day.append((day_k, {'label': label, 'disabled': disabled}))


    return events_by_day


def categorie_manager(categories=[]):
    frt_categories = []
    if hasattr(settings, 'CATEGORY_TO_HIGHLIGHT'):
        for category in categories:
            if category[0] == settings.CATEGORY_TO_HIGHLIGHT:
                frt_categories.append((category[0], {'class' : settings.CATEGORY_TO_HIGHLIGHT.lower(), 'label' : category[1]}))
            else :
                frt_categories.append(category)
    else :
        frt_categories = categories
    return frt_categories


def sign_url(input_url=None, secret=None):
    """ Sign a request URL with a URL signing secret.
      Source : https://developers.google.com/maps/documentation/maps-static/get-api-key
      Usage:
      from urlsigner import sign_url

      signed_url = sign_url(input_url=my_url, secret=SECRET)

      Args:
      input_url - The URL to sign
      secret    - Your URL signing secret

      Returns:
      The signed request URL

    """

    if not input_url or not secret:
      raise Exception("Both input_url and secret are required")

    url = urlparse(input_url)

    # We only need to sign the path+query part of the string
    url_to_sign = url.path.decode("utf-8") + "?" + url.query.decode("utf-8")

    # Decode the private key into its binary format
    # We need to decode the URL-encoded private key
    decoded_key = base64.urlsafe_b64decode(secret)

    # Create a signature using the private key and the URL-encoded
    # string using HMAC SHA1. This signature will be binary.
    signature = hmac.new(decoded_key, url_to_sign.encode('utf-8'), hashlib.sha1)

    # Encode the binary signature into base64 for use within a URL
    encoded_signature = base64.urlsafe_b64encode(signature.digest())

    original_url = url.scheme.decode("utf-8") + "://" + url.netloc.decode("utf-8") + url.path.decode("utf-8") + "?" + url.query.decode("utf-8")

    # Return signed URL
    return original_url  + "&signature=" + str(encoded_signature, 'utf-8')

