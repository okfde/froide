import re

from django import forms
from django.utils import timezone

from .models import UserPreference


class PreferenceVar:
    def __init__(self, value, form):
        self.value = value
        self.form = form


class Preference:
    def __init__(self, key: str, form_class):
        self.key = key
        self.form_class = form_class

    def __str__(self):
        return '<Preference {}>'.format(self.key)

    def get(self, user):
        if user is None or not user.is_authenticated:
            return None
        value = UserPreference.objects.get_preference(user, self.key)
        return PreferenceVar(value, self.form_class())


class PreferenceRegistry:
    def __init__(self):
        self.preferences = {}

    def register(self, key: str, form_class):
        form_class.initial_key = key
        pattern = re.compile(key)
        form_class.key_pattern = pattern
        self.preferences[pattern] = form_class
        return Preference(key, form_class)

    def find(self, key):
        for prefix, form in self.preferences.items():
            if prefix.match(key):
                return form
        raise KeyError


registry = PreferenceRegistry()


class PreferenceForm(forms.Form):
    key = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['key'].initial = self.initial_key

    def clean_key(self):
        key = self.cleaned_data['key']
        if not self.key_pattern.match(key):
            raise forms.ValidationError('Key does not match')
        return key

    def save(self, user):
        key = self.cleaned_data['key']
        value = self.cleaned_data['value']

        UserPreference.objects.update_or_create(
            user=user, key=key,
            defaults={
                'value': value,
                'timestamp': timezone.now()
            }
        )
