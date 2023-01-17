from django import forms
from django.urls import reverse

import pytest

from ..models import UserPreference
from ..preferences import PreferenceForm, registry


@pytest.fixture
def preference_key():
    class UserPreferenceForm(PreferenceForm):
        value = forms.TypedChoiceField(
            widget=forms.HiddenInput,
            choices=(
                (0, "0"),
                (1, "1"),
            ),
            coerce=lambda x: bool(int(x)),
        )

    preference_key = "test"
    registry.register(preference_key, UserPreferenceForm)
    return preference_key


def test_set_preferences_not_logged_in(client, preference_key):
    api_url = reverse("api-user-preference", kwargs={"key": preference_key})
    response = client.post(api_url, data={"value": "1"})
    assert response.status_code == 401


@pytest.mark.django_db
def test_set_preferences_logged_in(client, dummy_user, preference_key):
    assert UserPreference.objects.get_preference(dummy_user, preference_key) is None
    client.force_login(dummy_user)
    api_url = reverse("api-user-preference", kwargs={"key": preference_key})
    response = client.post(api_url, data={"value": "1"})
    assert response.status_code == 200
    assert UserPreference.objects.get_preference(dummy_user, preference_key) is True


@pytest.mark.django_db
def test_set_preferences_bad_format(client, dummy_user, preference_key):
    assert UserPreference.objects.get_preference(dummy_user, preference_key) is None
    client.force_login(dummy_user)
    api_url = reverse("api-user-preference", kwargs={"key": preference_key})
    response = client.post(api_url, data={"value": "blub"})
    assert response.status_code == 400
    assert UserPreference.objects.get_preference(dummy_user, preference_key) is None
