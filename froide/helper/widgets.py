from django import forms
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

class EmailInput(forms.TextInput):
    input_type = 'email'

class AgreeCheckboxInput(forms.CheckboxInput):
    def __init__(self, attrs=None, check_test=bool, agree_to="", url_name=None):
        super(AgreeCheckboxInput, self).__init__(attrs, check_test)
        self.agree_to = agree_to
        self.url_name = url_name

    def render(self, name, value, attrs=None):
        html = super(AgreeCheckboxInput, self).render(name, value, attrs)
        return mark_safe(u'%s <label for="id_%s">%s</label>' % (html, name, mark_safe(self.agree_to %
                {"url": reverse(self.url_name)})))
