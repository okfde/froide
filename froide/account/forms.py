from django import forms
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from helper.widgets import EmailInput

class NewUserForm(forms.Form):
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'placeholder': _('First Name'), 'class': 'inline'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(
        attrs={'placeholder': _('Last Name'), 'class': 'inline'}))
    email = forms.EmailField(widget=EmailInput(
        attrs={'placeholder': _('mail@ddress.net')}))

    def clean_first_name(self):
        return self.cleaned_data['first_name'].strip()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].strip()

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            pass
        else:
            raise forms.ValidationError(mark_safe(
                    _('This email address already has an account. <a href="%s?simple" class="target-small">Please login using that email address.</a>') % reverse("account-login")))

        return email

class UserLoginForm(forms.Form):
    email = forms.EmailField(widget=EmailInput(
        attrs={'placeholder': _('mail@ddress.net')}))
    password = forms.CharField(widget=forms.PasswordInput)
