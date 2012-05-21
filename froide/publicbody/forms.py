from django import forms
from django.utils.translation import ugettext as _

from helper.widgets import EmailInput


class PublicBodyForm(forms.Form):
    name = forms.CharField(label=_("Name of Public Body"))
    description = forms.CharField(label=_("Short description"),
        widget=forms.Textarea, required=False)
    email = forms.EmailField(widget=EmailInput,
        label=_("Email Address for Freedom of Information Requests"))
    url = forms.URLField(label=_("Homepage URL of Public Body"))
