from django import forms
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from froide.foirequest.auth import can_read_foirequest

from .models import FoiRequestFollower

User = get_user_model()


class FollowRequestForm(forms.Form):
    def __init__(self, foirequest, request, *args, **kwargs):
        self.foirequest = foirequest
        self.request = request
        self.user = request.user
        super(FollowRequestForm, self).__init__(*args, **kwargs)
        if not self.user.is_authenticated:
            self.fields["email"] = forms.EmailField(label=_("Your Email address"),
                    widget=forms.TextInput(attrs={"placeholder": _("email address")}))

    def clean(self):
        email = self.cleaned_data.get('email', None)
        if not self.user.is_authenticated and email is None:
            raise forms.ValidationError(_("Missing email address!"))
        if not can_read_foirequest(self.foirequest, self.request):
            raise forms.ValidationError(_("You cannot access this request!"))
        if not self.user.is_authenticated:
            try:
                User.objects.get(email=email)
            except User.DoesNotExist:
                pass
            else:
                raise forms.ValidationError(mark_safe(
                    _('This email address already has an account. <a href="%s?simple" class="target-small">Please login using that email address in order to follow this account.</a>') % reverse("account-login")))
        else:
            if self.user == self.foirequest.user:
                raise forms.ValidationError(_("You cannot follow your own requests."))
        return self.cleaned_data

    def save(self):
        return FoiRequestFollower.objects.follow(
            self.foirequest, self.user, **self.cleaned_data
        )
