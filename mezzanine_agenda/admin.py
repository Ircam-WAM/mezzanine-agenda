from __future__ import unicode_literals

from copy import deepcopy
from mezzanine.conf import settings

from django.contrib import admin
from mezzanine.core.admin import TeamOwnableAdmin
from mezzanine_agenda.models import Event, EventLocation, EventPrice, EventCategory,\
    ExternalShop, Season
from mezzanine_agenda.forms import EventAdminForm
from mezzanine.core.admin import DisplayableAdmin, OwnableAdmin,\
    BaseTranslationModelAdmin


class EventAdminBase(admin.ModelAdmin):

    model = Event


class EventAdmin(TeamOwnableAdmin, DisplayableAdmin):
    """
    Admin class for events.
    """

    fieldsets = deepcopy(EventAdminBase.fieldsets)
    exclude = ("short_url", )
    list_display = ["title", "start", "end", "user", "rank", "status", "admin_link"]
    if settings.EVENT_USE_FEATURED_IMAGE:
        list_display.insert(0, "admin_thumb")
    list_filter = deepcopy(DisplayableAdmin.list_filter) + ("location",)
    ordering = ('-start',)
    form = EventAdminForm

    def save_form(self, request, form, change):
        """
        Super class ordering is important here - user must get saved first.
        """
        OwnableAdmin.save_form(self, request, form, change)
        return DisplayableAdmin.save_form(self, request, form, change)


class EventLocationAdmin(admin.ModelAdmin):
    """
    Admin class for event locations. Hides itself from the admin menu
    unless explicitly specified.
    """

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "address",
                    "postal_code",
                    "city",
                    "room",
                    "mappable_location",
                    "lat",
                    "lon",
                    "description",
                    "link"
                )
            }
        ),
    )

    def in_menu(self):
        """
        Hide from the admin menu unless explicitly set in ``ADMIN_MENU_ORDER``.
        """
        for (name, items) in settings.ADMIN_MENU_ORDER:
            if "mezzanine_agenda.EventLocation" in items:
                return True
        return False


class SeasonAdminBase(admin.ModelAdmin):

    list_display = ["title", 'start', 'end']
    model = Season


class ExternalShopAdmin(BaseTranslationModelAdmin):

    model = ExternalShop


admin.site.register(Event, EventAdmin)
admin.site.register(EventLocation, EventLocationAdmin)
admin.site.register(EventPrice)
admin.site.register(EventCategory)
admin.site.register(ExternalShop, ExternalShopAdmin)
admin.site.register(Season, SeasonAdminBase)
