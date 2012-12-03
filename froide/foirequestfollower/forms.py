import floppyforms as forms

from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from froide.foirequest.models import User

from .models import FoiRequestFollower


class FollowRequestForm(forms.Form):
    def __init__(self, foirequest, user, *args, **kwargs):
        self.foirequest = foirequest
        self.user = user
        super(FollowRequestForm, self).__init__(*args, **kwargs)
        if not self.user.is_authenticated():
            self.fields["email"] = forms.EmailField(label=_("Your Email address"),
                    widget=forms.TextInput(attrs={"placeholder": _("email address")}))

    def clean(self):
        email = self.cleaned_data.get('email', None)
        if not self.user.is_authenticated() and email is None:
            raise forms.ValidationError(_("Missing email address!"))
        if not self.foirequest.is_visible(self.user):
            raise forms.ValidationError(_("You cannot access this request!"))
        if not self.user.is_authenticated():
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
        return FoiRequestFollower.objects.follow(self.foirequest, self.user, **self.cleaned_data)
