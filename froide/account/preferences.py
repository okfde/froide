import re
from typing import Sequence

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


def get_preferences_for_user(user, preferences: Sequence[Preference]):
    prefs_map = {p.key: p for p in preferences}
    value_map = dict(
        UserPreference.objects.filter(
            user=user, key__in=list(prefs_map.keys())
        ).values_list('key', 'value')
    )
    return {
        key: PreferenceVar(value_map.get(key), p.form_class())
        for key, p in prefs_map.items()
    }


class PreferenceRegistry:
    def __init__(self):
        self.preferences = {}

    def register(self, key: str, form_class):
        pattern = re.compile(key)
        # Create a subclass so a class can be used
        # with multiple keys
        key_form_class = type(key.title(), (form_class,), {
            'initial_key': key,
            'key_pattern': pattern
        })
        self.preferences[pattern] = key_form_class
        return Preference(key, key_form_class)

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
