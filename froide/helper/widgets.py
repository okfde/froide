import floppyforms as forms

from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe


class PriceInput(forms.TextInput):
    template_name = "bootstrap/price_input.html"

    def get_context(self, name, value, attrs):
        ctx = super(PriceInput, self).get_context(name, value, attrs)
        ctx['attrs']['class'] = 'input-mini'
        return ctx


class AgreeCheckboxInput(forms.CheckboxInput):
    def __init__(self, attrs=None, check_test=bool, agree_to="", url_names=None):
        super(AgreeCheckboxInput, self).__init__(attrs, check_test)
        self.agree_to = agree_to
        self.url_names = url_names

    def render(self, name, value, attrs=None):
        html = super(AgreeCheckboxInput, self).render(name, value, attrs)
        return mark_safe(u'<label class="checkbox">%s %s</label>' % (html, self.agree_to %
                dict([(k, reverse(v)) for k, v in self.url_names.items()])))
