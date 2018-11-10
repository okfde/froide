from django import forms
from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from .models import AccessToken
from .widgets import TokenWidget
from .utils import get_signed_purpose, unsign_purpose


def clean_purpose(field):
    def clean(self):
        signed_purpose = self.cleaned_data[field]
        if not signed_purpose:
            return ''
        purpose = unsign_purpose(signed_purpose)
        if purpose is None:
            raise forms.ValidationError('Bad purpose')
        return purpose
    return clean


class ResetTokenForm(forms.Form):
    create = forms.CharField(required=False)
    remove = forms.CharField(required=False)
    reset = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    clean_create = clean_purpose('create')
    clean_remove = clean_purpose('remove')
    clean_reset = clean_purpose('reset')

    def save(self):
        for action in ('reset', 'remove', 'create'):
            if self.cleaned_data.get(action):
                break
        purpose = self.cleaned_data[action]
        if action == 'reset':
            AccessToken.objects.reset(
                user=self.user, purpose=purpose
            )
            return _('URL has been reset.')
        elif action == 'create':
            AccessToken.objects.create_for_user(self.user, purpose=purpose)
            return _('URL has been created.')
        else:
            AccessToken.objects.filter(user=self.user, purpose=purpose).delete()
            return _('URL has been removed.')


class AccessTokenForm(forms.Form):
    token = forms.CharField(
        widget=TokenWidget(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        purpose = kwargs.pop('purpose')
        label = kwargs.pop('label')
        url_name = kwargs.pop('url_name')
        url_kwargs = kwargs.pop('url_kwargs')

        super().__init__(*args, **kwargs)

        self.fields['token'].label = label
        widget = self.fields['token'].widget

        ctx = {
            'purpose': get_signed_purpose(purpose),
        }

        token = AccessToken.objects.get_token_by_user(user, purpose)
        if token is not None:
            url_kwargs['token'] = token
            value = settings.SITE_URL + reverse(url_name, kwargs=url_kwargs)
            self.fields['token'].initial = value
            ctx['url'] = value
        ctx['token'] = token
        widget.extra_context = ctx
