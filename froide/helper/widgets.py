from __future__ import unicode_literals

from django import forms
from django.utils.safestring import mark_safe

from django.forms.widgets import TextInput
from django.conf import settings
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from taggit.utils import edit_string_for_tags


class BootstrapChoiceMixin(object):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {})
        kwargs['attrs'].update({'class': 'form-check-input'})
        super(BootstrapChoiceMixin, self).__init__(*args, **kwargs)


class BootstrapCheckboxInput(BootstrapChoiceMixin, forms.CheckboxInput):
    pass


class BootstrapRadioSelect(BootstrapChoiceMixin, forms.RadioSelect):
    option_template_name = 'helper/forms/widgets/radio_option.html'


class PriceInput(forms.TextInput):
    template_name = "helper/forms/widgets/price_input.html"

    def get_context(self, name, value, attrs):
        ctx = super(PriceInput, self).get_context(name, value, attrs)
        ctx['widget'].setdefault('attrs', {})
        ctx['widget']['attrs']['class'] = 'form-control col-3'
        ctx['currency'] = settings.FROIDE_CONFIG['currency']
        return ctx


class TagAutocompleteTagIt(TextInput):
    """
    From https://github.com/nemesisdesign/django-tagging-autocomplete-tag-it

    Copyright (c) 2009 Ludwik Trammer

    """

    class Media:
        # JS Base url defaults to STATIC_URL/jquery-autocomplete/
        js_base_url = 'js/libs/jquery-tag-it/'
        # jQuery ui is loaded from google's CDN by default
        jqueryui_file = 'js/libs/jquery-ui.min.js'

        # load js
        js = (
            'admin/js/vendor/jquery/jquery.min.js',
            '%stagging_autocomplete_tagit.js' % js_base_url,
            jqueryui_file,
            '%sjquery.tag-it.min.js' % js_base_url,
        )

        # custom css can also be overriden in settings
        css_list = getattr(settings, 'TAGGING_AUTOCOMPLETE_CSS',
            ['%scss/ui-autocomplete-tag-it.css' % js_base_url])
        # check is a list, if is a string convert it to a list
        if type(css_list) != list and type(css_list) == str:
            css_list = [css_list]
        css = {
            'screen': css_list
        }

    def __init__(self, *args, **kwargs):
        self.max_tags = getattr(settings, 'TAGGING_AUTOCOMPLETE_MAX_TAGS', 20)
        self.tag_filter = kwargs.pop('tag_filter', None)
        self.autocomplete_url = kwargs.pop('autocomplete_url', None)
        super(TagAutocompleteTagIt, self).__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        """ Force comma separation of tags by adding trailing comma """
        val = data.get(name, None)
        if val is None:
            return None
        return val + ','

    def render(self, name, value, attrs=None, renderer=None):
        """ Render HTML code """
        if value is not None and not isinstance(value, six.string_types):
            value = edit_string_for_tags([o.tag for o in value.select_related("tag")])
        # django-tagging
        case_sensitive = 'true' if not getattr(settings, 'FORCE_LOWERCASE_TAGS', False) else 'false'
        max_tag_lentgh = getattr(settings, 'MAX_TAG_LENGTH', 50)
        # django-tagging-autocomplete-tagit
        autocomplete_min_length = getattr(settings, 'TAGGING_AUTOCOMPLETE_MIN_LENGTH', 3)
        remove_confirmation = 'true' if getattr(settings, 'TAGGING_AUTOCOMPLETE_REMOVE_CONFIRMATION', True) else 'false'
        animate = 'true' if getattr(settings, 'TAGGING_AUTOCOMPLETE_ANIMATE', True) else 'false'
        html = super(TagAutocompleteTagIt, self).render(name, value, attrs, renderer=renderer)
        # Subclass this field in case you need to add some custom behaviour like custom callbacks
        js = """<script type="text/javascript">window.init_jQueryTagit = window.init_jQueryTagit || [];
                window.init_jQueryTagit.push({{
                    objectId: '{objectid}',
                    sourceUrl: '{sourceurl}',
                    fieldName: '{fieldname}',
                    minLength: {minlength},
                    removeConfirmation: {removeConfirmation},
                    caseSensitive: {caseSensitive},
                    animate: {animate},
                    maxLength: {maxLength},
                    maxTags: {maxTags},
                    allowSpaces: true,
                    onTagAdded  : null,
                    onTagRemoved: null,
                    onTagClicked: null,
                    onMaxTagsExceeded: null,
                    placeholderText: '{placeholderText}',
                    kind: '{kind}'
                }});
            </script>""".format(
                objectid=attrs['id'],
                sourceurl=self.autocomplete_url() if callable(self.autocomplete_url) else self.autocomplete_url,
                fieldname=name,
                minlength=autocomplete_min_length,
                removeConfirmation=remove_confirmation,
                caseSensitive=case_sensitive,
                animate=animate,
                maxLength=max_tag_lentgh,
                maxTags=self.max_tags,
                placeholderText=_('Enter comma-separated tags here'),
                kind=self.tag_filter or ''
        )

        return mark_safe("\n".join([html, js]))
