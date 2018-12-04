from django import forms
from django.utils.safestring import mark_safe

from django.conf import settings
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _

from taggit.utils import edit_string_for_tags, parse_tags


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


class TagAutocompleteWidget(forms.TextInput):
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
        super(TagAutocompleteWidget, self).__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        """ Force comma separation of tags by adding trailing comma """
        val = data.get(name, None)
        if val is None:
            return None
        return val + ','

    def render(self, name, value, attrs=None, renderer=None):
        """ Render HTML code """
        if value is not None and not isinstance(value, str):
            value_list = [o.tag for o in value.select_related('tag')]
            value = edit_string_for_tags(value_list)

        options = [
            '<option value="{value}" selected>{value}</option>'.format(
                value=escape(str(o))) for o in parse_tags(value)]
        options = '\n'.join(options)

        context = {
            'data-additemtext': _('Press Enter to add <b>${value}</b>'),
            'data-uniqueitemtext': _('This tag is already set.'),
            'data-loading': _('Searching…'),
            'data-noresults': _('No results'),
            'data-nochoices': _('No results'),
            'data-fetchurl': self.autocomplete_url
        }
        context = {k: escape(v) for k, v in context.items()}
        context = ['%s="%s"' % (k, v) for k, v in context.items()]

        html = super(TagAutocompleteWidget, self).render(
            name, value, attrs, renderer=renderer
        )
        html = """<div style="display: none">{input}</div>
        <select class="tagautocomplete"
        {dataitems}
        id="{objectid}_select" multiple>{options}</select>""".format(
                input=html,
                objectid=attrs['id'],
                options=options,
                dataitems=' '.join(context)
        )
        return mark_safe(html)
