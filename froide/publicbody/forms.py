from django import forms
from django.utils.translation import ugettext_lazy as _

from froide.helper.form_utils import JSONMixin

from .models import PublicBody
from .widgets import PublicBodySelect


class PublicBodyForm(JSONMixin, forms.Form):
    publicbody = forms.ModelChoiceField(
            queryset=PublicBody.objects.all(),
            widget=PublicBodySelect,
            label=_("Search for a topic or a public body:")
    )

    def as_data(self):
        data = super(PublicBodyForm, self).as_data()
        if self.is_bound and self.is_valid():
            data['cleaned_data'] = self.cleaned_data
        return data


class MultiplePublicBodyForm(JSONMixin, forms.Form):
    publicbody = forms.ModelMultipleChoiceField(
            queryset=PublicBody.objects.all(),
            label=_("Search for a topic or a public body:")
    )
