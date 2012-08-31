from django import forms
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe


class EmailInput(forms.TextInput):
    input_type = 'email'


class DateInput(forms.DateInput):
    input_type = 'date'


class AgreeCheckboxInput(forms.CheckboxInput):
    def __init__(self, attrs=None, check_test=bool, agree_to="", url_names=None):
        super(AgreeCheckboxInput, self).__init__(attrs, check_test)
        self.agree_to = agree_to
        self.url_names = url_names

    def render(self, name, value, attrs=None):
        html = super(AgreeCheckboxInput, self).render(name, value, attrs)
        return mark_safe(u'%s <label for="id_%s">%s</label>' % (html, name, self.agree_to %
                dict([(k, reverse(v)) for k, v in self.url_names.items()])))
