from django import forms
from django.conf import settings

from taggit.forms import TagWidget


class BootstrapChoiceMixin(object):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {})
        kwargs['attrs'].update({'class': 'form-check-input'})
        super(BootstrapChoiceMixin, self).__init__(*args, **kwargs)


class BootstrapCheckboxInput(BootstrapChoiceMixin, forms.CheckboxInput):
    pass


class BootstrapRadioSelect(BootstrapChoiceMixin, forms.RadioSelect):
    option_template_name = 'helper/forms/widgets/radio_option.html'


class BootstrapFileInput(forms.FileInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {})
        kwargs['attrs'].update({'class': 'form-control'})
        super(BootstrapFileInput, self).__init__(*args, **kwargs)


class PriceInput(forms.TextInput):
    template_name = "helper/forms/widgets/price_input.html"

    def get_context(self, name, value, attrs):
        ctx = super(PriceInput, self).get_context(name, value, attrs)
        ctx['widget'].setdefault('attrs', {})
        ctx['widget']['attrs']['class'] = 'form-control col-3'
        ctx['widget']['attrs']['pattern'] = "[\\d\\.,]*"
        ctx['currency'] = settings.FROIDE_CONFIG['currency']
        return ctx


class TagAutocompleteWidget(TagWidget):
    template_name = 'helper/forms/widgets/tag_autocomplete.html'

    class Media:

        js = (
            'js/tagautocomplete.js',
        )

        css_list = [
            'css/tagautocomplete.css'
        ]
        css = {
            'screen': css_list
        }

    def __init__(self, *args, **kwargs):
        self.autocomplete_url = kwargs.pop('autocomplete_url', None)
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx['autocomplete_url'] = self.autocomplete_url
        ctx['tags'] = [v.tag.name for v in value]
        return ctx
