from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from froide.account.forms import user_extra_registry
from froide.foirequest.auth import can_read_foirequest

from .models import FoiRequestFollower

User = get_user_model()


class FollowRequestForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.foirequest = kwargs.pop('foirequest')
        self.request = kwargs.pop('request')
        self.user = self.request.user
        super().__init__(*args, **kwargs)
        if not self.user.is_authenticated:
            self.fields["email"] = forms.EmailField(
                label=_("Your Email address"),
                widget=forms.EmailInput(
                    attrs={
                        "placeholder": _("email address"),
                        "class": "form-control",
                        'autocomplete': 'email'
                    }
                )
            )
            user_extra_registry.on_init('follow', self)

    def clean(self):
        email = self.cleaned_data.get('email', None)
        if not self.user.is_authenticated and email is None:
            raise forms.ValidationError(_("Missing email address!"))
        if not can_read_foirequest(self.foirequest, self.request):
            raise forms.ValidationError(_("You cannot access this request!"))
        if self.user == self.foirequest.user:
            raise forms.ValidationError(_("You cannot follow your own requests."))
        return self.cleaned_data

    def save(self):
        return FoiRequestFollower.objects.follow(
            self.foirequest, self.user, **self.cleaned_data
        )
