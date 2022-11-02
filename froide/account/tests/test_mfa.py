import re
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.urls import reverse

import pytest
from mfa.models import MFAKey


@pytest.fixture
def mfa_user(dummy_user):
    MFAKey.objects.create(user=dummy_user, method="recovery")
    yield dummy_user


@pytest.mark.django_db
def test_mfa_after_password(client, mfa_user):
    response = client.post(
        reverse("account-login"),
        data={"username": mfa_user.email, "password": "froide"},
    )
    assert response.status_code == 302
    assert reverse("mfa:auth", kwargs={"method": "recovery"}) in response["Location"]
    # not logged in
    response = client.get(reverse("account-requests"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_recently_authenticated(client, mfa_user):
    client.login(email=mfa_user.email, password="froide")
    # oauth app list is protected by recently authenticated wrapper

    response = client.get(reverse("oauth2_provider:list"))
    # Works right afer login
    assert response.status_code == 200

    # Patch recent auth duration to negative
    with mock.patch("froide.account.auth.RECENT_AUTH_DURATION", -timedelta(seconds=1)):
        response = client.get(reverse("oauth2_provider:list"))
    assert response.status_code == 302
    assert reverse("account-reauth") in response["Location"]


@pytest.mark.django_db
def test_password_reset_mfa_no_login(client, mfa_user):
    data = {"pwreset-email": mfa_user.email}
    response = client.post(reverse("account-send_reset_password_link"), data)
    assert response.status_code == 302
    message = mail.outbox[0]
    match = re.search(r"/account/reset/([^/]+)/([^/]+)/", message.body)
    uidb64 = match.group(1)
    token = match.group(2)
    response = client.get(
        reverse(
            "account-password_reset_confirm",
            kwargs={"uidb64": uidb64, "token": token},
        ),
        follow=True,
    )
    assert response.status_code == 200
    data = {"new_password1": "froide4froide5", "new_password2": "froide4froide5"}
    response = client.post(response.wsgi_request.path, data)
    assert response.status_code == 302
    assert reverse("mfa:auth", kwargs={"method": "recovery"}) in response["Location"]
    # We are not logged in
    response = client.get(reverse("account-requests"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_go_with_mfa(client, mfa_user):
    test_url = reverse("account-requests")

    # Try logging in via link: success
    autologin = mfa_user.get_autologin_url(test_url)
    response = client.get(autologin)
    assert response.status_code == 200
    response = client.post(autologin)
    assert response.status_code == 302

    assert reverse("mfa:auth", kwargs={"method": "recovery"}) in response["Location"]

    # We are not logged in
    response = client.get(test_url)
    assert response.status_code == 302


def test_admin_login_url(client):
    admin_login_url = reverse("admin:login")

    response = client.get(admin_login_url)
    # Admin login page redirects to account login page
    assert response.status_code == 302
    assert reverse("account-login") in response["Location"]
