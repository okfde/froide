import re
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core import mail
from django.urls import URLResolver, reverse

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
    response = client.get(response["Location"])
    assert response.context["user"].is_anonymous


@pytest.mark.django_db
def test_go_with_mfa_login_optional(client, mfa_user):
    test_url = "/"

    # Try logging in via link: success
    autologin = mfa_user.get_autologin_url(test_url)
    response = client.get(autologin + "?nologin=1")
    assert response.status_code == 200
    response = client.post(autologin, data={"nologin": "1"})
    assert response.status_code == 302

    assert response["Location"] == test_url
    # We are not logged in
    response = client.get(test_url)
    assert response.status_code == 200
    assert response.context["user"].is_anonymous


def test_admin_login_url(client):
    admin_login_url = reverse("admin:login")

    response = client.get(admin_login_url)
    # Admin login page redirects to account login page
    assert response.status_code == 302
    assert reverse("account-login") in response["Location"]


@pytest.mark.django_db
def test_admin_apps_for_login(client, dummy_user):
    """Test that any installed admin apps do not provide login functionality."""

    def get_login_path(resolver):
        for pattern in resolver.url_patterns:
            if pattern.name == "login":
                yield reverse(
                    "%s:%s" % (resolver.namespace, pattern.name),
                    current_app=resolver.app_name,
                )
                break

    def get_admins(pattern_list):
        for item in pattern_list:
            if not isinstance(item, URLResolver):
                continue
            if item.app_name == "admin":
                yield item
            else:
                yield from get_admins(item.url_patterns)

    patterns = __import__(settings.ROOT_URLCONF, {}, {}, [""]).urlpatterns

    dummy_user.is_staff = True
    dummy_user.save()
    login_url = reverse("account-login")

    admin_resolvers = get_admins(patterns)
    admin_login_paths = [
        cb for resolver in admin_resolvers for cb in get_login_path(resolver)
    ]
    for login_path in admin_login_paths:
        response = client.get(login_path)
        assert response.status_code == 302
        assert response["Location"].startswith(login_url)

        response = client.post(
            login_path, {"username": dummy_user.email, "password": "froide"}
        )
        assert client.session.get("_auth_user_id") is None
        assert response.status_code == 302
        assert response["Location"].startswith(login_url)
