from modeltranslation.translator import register, TranslationOptions

from mezzanine_agenda.models import Event, EventLocation, EventCategory, ExternalShop


@register(Event)
class EventTranslationOptions(TranslationOptions):

    fields = (
        'title',
        'sub_title',
        'description',
        'content',
        'mentions',
        'no_price_comments'
    )


@register(EventLocation)
class EventLocationTranslationOptions(TranslationOptions):

    fields = ('description',)


@register(EventCategory)
class EventCategoryTranslationOptions(TranslationOptions):

    fields = ('name', 'description')


@register(ExternalShop)
class ExternalShopTranslationOptions(TranslationOptions):

    fields = ('title',)
