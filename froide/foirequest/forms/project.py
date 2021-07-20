from django import forms
from django.utils.translation import gettext_lazy as _

from froide.helper.widgets import BootstrapCheckboxInput


class MakeProjectPublicForm(forms.Form):
    publish_requests = forms.BooleanField(
        required=False,
        widget=BootstrapCheckboxInput,
        label=_("Publish all requests"),
    )
