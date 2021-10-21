from django import forms
from mezzanine_agenda.models import EventCategory, EventLocation, EventPrice
from dal import autocomplete


class EventFilterForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(EventFilterForm, self).__init__(*args, **kwargs)
        event_categories = EventCategory.objects.all()
        event_categories = [(cat.name, cat.name) for cat in event_categories]
        event_locations = EventLocation.objects.distinct('title')
        event_locations = [(loc.title, loc.title) for loc in event_locations]
        self.fields['event_categories_filter'] = forms.MultipleChoiceField(
            required=False,
            widget=forms.CheckboxSelectMultiple,
            choices=event_categories,
        )
        self.fields['event_locations_filter'] = forms.MultipleChoiceField(
            required=False,
            widget=forms.CheckboxSelectMultiple,
            choices=event_locations,
        )


class EventAdminForm(forms.ModelForm):

    class Meta:
        model = EventPrice
        fields = ('__all__')
        widgets = {
            'prices': autocomplete.ModelSelect2Multiple(
                url='event-price-autocomplete',
                attrs={'data-html': True}
            )
        }
