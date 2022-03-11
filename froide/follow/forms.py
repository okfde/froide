from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from froide.account.forms import user_extra_registry
from froide.helper.spam import SpamProtectionMixin

User = get_user_model()


class FollowForm(SpamProtectionMixin, forms.Form):
    SPAM_PROTECTION = {
        "timing": False,
        "captcha": "ip",
        "action": "follow_request",
        "action_limit": 3,
        "action_block": True,
    }

    def __init__(self, *args, **kwargs):
        self.content_object = kwargs.pop("content_object")
        self.configuration = kwargs.pop("configuration")
        self.request = kwargs.pop("request")
        self.user = self.request.user
        super().__init__(*args, **kwargs)
        if not self.user.is_authenticated:
            self.fields["email"] = forms.EmailField(
                label=_("Your email address"),
                widget=forms.EmailInput(
                    attrs={
                        "placeholder": _("email address"),
                        "class": "form-control",
                        "autocomplete": "email",
                    }
                ),
            )
            user_extra_registry.on_init("follow", self)

    def clean(self):
        email = self.cleaned_data.get("email", None)
        if not self.user.is_authenticated and email is None:
            raise forms.ValidationError(_("Missing email address!"))

        if not self.configuration.can_follow(
            self.content_object, self.user, request=self.request
        ):
            raise forms.ValidationError(_("You cannot follow this!"))

        user_extra_registry.on_clean("follow", self)

        super().clean()
        return self.cleaned_data

    def save(self):
        user_extra_registry.on_save("follow", self, self.user)
        return self.configuration.model.objects.follow(
            self.content_object, self.user, **self.cleaned_data
        )
