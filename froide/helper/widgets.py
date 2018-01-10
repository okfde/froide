from __future__ import unicode_literals

from django import forms
from django.utils.safestring import mark_safe

from django.conf import settings
from django.utils import six
from django.utils.html import escape

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


class PriceInput(forms.TextInput):
    template_name = "helper/forms/widgets/price_input.html"

    def get_context(self, name, value, attrs):
        ctx = super(PriceInput, self).get_context(name, value, attrs)
        ctx['widget'].setdefault('attrs', {})
        ctx['widget']['attrs']['class'] = 'form-control col-3'
        ctx['currency'] = settings.FROIDE_CONFIG['currency']
        return ctx


class TagAutocompleteWidget(forms.TextInput):
    class Media:

        js = (
            'https://code.jquery.com/jquery-3.2.1.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.4/js/select2.min.js'
        )

        css_list = [
            'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.4/css/select2.min.css'
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
        options = ''
        if value is not None and not isinstance(value, six.string_types):
            value = [o.tag for o in value.select_related('tag')]
            value = edit_string_for_tags(value)

            options = [
                '<option value="{value}" selected>{value}</option>'.format(
                    value=escape(six.text_type(o))) for o in parse_tags(value)]
            options = '\n'.join(options)

        html = super(TagAutocompleteWidget, self).render(
            name, value, attrs, renderer=renderer
        )

        html = """<div style="display: none">%(input)s</div><select id="%(objectid)s_select2" name="%(objectid)s_select2" multiple>%(options)s</select>
        <script type="text/javascript">
            document.addEventListener('DOMContentLoaded', function() {
                $('#%(objectid)s_select2').on('change.select2', function(e) {
                    var tagString = $(this).select2('data').map(function(el){
                        return '"' + el.id + '"';
                    }).join(', ');
                    $('#%(objectid)s').val(tagString);
                }).select2({
                    width: '75%%',
                    tags: true,
                    tokenSeparators: [',', ' '],
                    ajax: {
                        url: '%(sourceurl)s',
                        data: function (params) {
                            if (params.term.length === 0) {
                                return null;
                            }
                            return { query: params.term };
                        },
                        processResults: function(data) {
                            return { results: data.map(function(el) {
                                    return { id: el, text: el }
                                })
                            }
                        }
                    }
                })
            });
            </script>""" % dict(
                input=html,
                objectid=attrs['id'],
                sourceurl=self.autocomplete_url,
                options=options
        )

        return mark_safe(html)
