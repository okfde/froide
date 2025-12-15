import re
from datetime import datetime, timedelta, timezone
from unittest import mock
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage import default_storage
from django.core import mail
from django.db import IntegrityError
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import escape

import pytest

from froide.accesstoken.models import AccessToken
from froide.account.factories import UserFactory
from froide.account.management.commands.send_mass_mail import Command
from froide.foirequest.models import FoiMessage, FoiRequest
from froide.foirequest.tests import factories
from froide.foirequestfollower.models import FoiRequestFollower
from froide.publicbody.models import PublicBody

from ..admin import UserAdmin
from ..models import AccountBlocklist
from ..services import AccountService
from ..utils import merge_accounts

User = get_user_model()

SPAM_ENABLED_CONFIG = dict(settings.FROIDE_CONFIG)
SPAM_ENABLED_CONFIG["spam_protection"] = True


@pytest.mark.django_db
def test_account_page(world, client):
    ok = client.login(email="info@fragdenstaat.de", password="wrong")
    assert not ok
    ok = client.login(email="info@fragdenstaat.de", password="froide")
    assert ok
    response = client.get(reverse("account-requests"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_account_drafts(world, client, request_draft_factory):
    response = client.get(reverse("account-drafts"))
    assert response.status_code == 302
    ok = client.login(email="info@fragdenstaat.de", password="froide")
    assert ok

    user = User.objects.get(email="info@fragdenstaat.de")
    draft = request_draft_factory(user=user)

    response = client.get(reverse("account-drafts"))
    assert response.status_code == 200
    assert draft.subject in str(response.content)
    assert escape(draft.get_absolute_url()) in str(response.content)


@pytest.mark.django_db
def test_account_following(world, client):
    response = client.get(reverse("account-following"))
    assert response.status_code == 302
    ok = client.login(email="info@fragdenstaat.de", password="froide")
    assert ok

    response = client.get(reverse("account-following"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_page(world, client):
    response = client.get(reverse("account-requests"))
    assert response.status_code == 302
    client.get(reverse("account-login"))
    response = client.post(
        reverse("account-login"),
        {"username": "doesnt@exist.com", "password": "foobar"},
    )
    assert response.status_code == 200
    response = client.post(
        reverse("account-login"),
        {"username": "info@fragdenstaat.de", "password": "dummy"},
    )
    assert response.status_code == 200
    response = client.post(
        reverse("account-login"),
        {"username": "info@fragdenstaat.de", "password": "froide"},
    )
    assert response.status_code == 302
    response = client.get(reverse("account-requests"))
    assert response.status_code == 200
    response = client.post(
        reverse("account-login"),
        {"username": "info@fragdenstaat.de", "password": "froide"},
    )
    # already logged in, login again gives 302
    assert response.status_code == 302
    assert response.url in reverse("account-show")
    # logout only via POST
    response = client.get(reverse("account-logout"))
    assert response.status_code == 405
    response = client.post(reverse("account-logout"))
    assert response.status_code == 302

    user = User.objects.get(email="info@fragdenstaat.de")
    user.is_active = False
    user.save()
    client.logout()
    response = client.post(
        reverse("account-login"),
        {"email": "info@fragdenstaat.de", "password": "froide"},
    )
    # inactive users can't login via password
    assert response.status_code == 200
    response = client.get(reverse("account-requests"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_signup(world, client):
    mail.outbox = []
    post = {
        "first_name": "Horst",
        "last_name": "Porst",
        "terms": "on",
        "private": True,
        "user_email": "horst.porst",
        "time": (datetime.now(timezone.utc) - timedelta(seconds=30)).timestamp(),
    }
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 302
    assert response.url == "/account/"

    assert len(mail.outbox) == 0
    client.logout()
    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 200
    post["user_email"] = "horst.porst@example.com"
    post["address"] = "MyOwnPrivateStree 5\n31415 Pi-Ville"

    response = client.post(reverse("account-signup"), post)

    assert response.status_code == 302
    new_account_url = reverse("account-new")
    assert new_account_url in response.url

    user = User.objects.get(email=post["user_email"])
    assert user.first_name == post["first_name"]
    assert user.last_name == post["last_name"]
    assert user.address == post["address"]
    assert mail.outbox[0].to[0] == post["user_email"]

    # sign up with email that is not confirmed
    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 302

    # sign up with email that is confirmed
    message = mail.outbox[0]
    match = re.search(r"/%d/(\w+)/" % user.pk, message.body)
    response = client.get(
        reverse(
            "account-confirm", kwargs={"user_id": user.pk, "secret": match.group(1)}
        )
    )
    assert response.status_code == 302
    client.logout()
    user = User.objects.get(id=user.pk)
    assert user.is_active
    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 302


@pytest.mark.django_db
def test_overlong_name_signup(world, client):
    post = {
        "first_name": "Horst" * 6 + "a",
        "last_name": "Porst" * 6,
        "terms": "on",
        "private": True,
        "user_email": "horst.porst@example.com",
        "address": "MyOwnPrivateStree 5\n31415 Pi-Ville",
        "time": (datetime.now(timezone.utc) - timedelta(seconds=30)).timestamp(),
    }
    client.logout()
    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 200
    post["first_name"] = post["first_name"][:-1]
    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 302


@pytest.mark.django_db
@override_settings(FROIDE_CONFIG=SPAM_ENABLED_CONFIG)
def test_signup_too_fast(world, client):
    post = {
        "first_name": "Horst",
        "last_name": "Porst",
        "terms": "on",
        "private": True,
        "user_email": "horst.porst@example.com",
        "address": "MyOwnPrivateStree 5\n31415 Pi-Ville",
        # Signup in less than 5 seconds
        "time": (datetime.now(timezone.utc) - timedelta(seconds=3)).timestamp(),
    }
    client.logout()
    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 200


@pytest.mark.django_db
def test_signup_same_name(world, client):
    client.logout()
    post = {
        "first_name": "Horst",
        "last_name": "Porst",
        "terms": "on",
        "private": True,
        "user_email": "horst.porst@example.com",
        "address": "MyOwnPrivateStree 5\n31415 Pi-Ville",
        "time": (datetime.now(timezone.utc) - timedelta(seconds=30)).timestamp(),
    }
    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 302
    post["user_email"] = "horst.porst2@example.com"
    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 302
    user = User.objects.get(email="horst.porst2@example.com")
    assert user.username == "h.porst_1"


@pytest.mark.django_db
def test_confirmation_process(world, client):
    user, user_created = AccountService.create_user(
        first_name="Stefan",
        last_name="Wehrmeyer",
        user_email="sw@example.com",
        address="SomeRandomAddress\n11234 Bern",
        private=True,
    )
    AccountService(user).send_confirmation_mail()
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    match = re.search(r"/%d/(\w+)/" % user.pk, message.body)
    response = client.get(
        reverse(
            "account-confirm", kwargs={"user_id": user.pk, "secret": match.group(1)}
        )
    )
    assert response.status_code == 302
    assert reverse("account-show") in response.url
    response = client.get(response.url)
    assert response.status_code == 200
    response = client.get(reverse("account-requests"))
    assert response.status_code == 200
    response = client.get(
        reverse("account-confirm", kwargs={"user_id": user.pk, "secret": "a" * 32})
    )
    assert response.status_code == 302
    client.logout()
    response = client.get(
        reverse(
            "account-confirm", kwargs={"user_id": user.pk, "secret": match.group(1)}
        )
    )
    # user is already active, link does not exist
    assert response.status_code == 302
    assert response["Location"] == reverse("account-login")
    # deactivate user
    user = User.objects.get(pk=user.pk)
    user.is_active = False
    # set last_login back artificially so it's not the same
    # as in secret link
    user.last_login = user.last_login - timedelta(seconds=10)
    user.save()
    response = client.get(
        reverse(
            "account-confirm", kwargs={"user_id": user.pk, "secret": match.group(1)}
        )
    )
    # user is inactive, but link was already used
    assert response.status_code == 302
    assert reverse("account-login") in response.url


@pytest.mark.django_db
def test_next_link_login(world, client):
    mes = FoiMessage.objects.all()[0]
    url = mes.get_absolute_url()
    enc_url = url.replace("#", "%23")  # FIXME: fake uri encode
    response = client.get(reverse("account-login") + "?next=%s" % enc_url)
    # occurences in hidden inputs of login, signup and forgotten password
    assert response.content.decode("utf-8").count(url) == 2
    response = client.post(
        reverse("account-login"),
        {"username": "info@fragdenstaat.de", "next": url, "password": "froide"},
    )
    assert response.status_code == 302
    assert response.url.endswith(url)


@pytest.mark.django_db
def test_next_link_signup(world, client):
    mail.outbox = []
    mes = FoiMessage.objects.all()[0]
    url = mes.get_absolute_url()
    post = {
        "first_name": "Horst",
        "last_name": "Porst",
        "terms": "on",
        "private": True,
        "user_email": "horst.porst@example.com",
        "address": "MyOwnPrivateStree 5\n31415 Pi-Ville",
        "next": url,
        "time": (datetime.now(timezone.utc) - timedelta(seconds=30)).timestamp(),
    }
    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 302
    new_account_url = reverse("account-new")
    assert new_account_url in response.url

    user = User.objects.get(email=post["user_email"])
    message = mail.outbox[0]
    match = re.search(r"/%d/(\w+)/" % user.pk, message.body)
    response = client.get(
        reverse(
            "account-confirm", kwargs={"user_id": user.pk, "secret": match.group(1)}
        )
    )
    assert response.status_code == 302
    assert response.url.endswith(url)


@pytest.mark.django_db
def test_change_password(world, client):
    response = client.get(reverse("account-change_password"))
    assert response.status_code == 405
    data = {"new_password1": "froide1froide2", "new_password2": "froide1froide3"}
    response = client.post(reverse("account-change_password"), data)
    assert response.status_code == 302
    assert reverse("account-login") in response["Location"]
    assert "?next=" in response["Location"]

    ok = client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(reverse("account-change_password"), data)
    assert response.status_code == 400
    data["new_password2"] = "froide1froide2"
    response = client.post(reverse("account-change_password"), data)
    assert response.status_code == 302
    client.logout()
    ok = client.login(email="info@fragdenstaat.de", password="froide")
    assert not ok
    ok = client.login(email="info@fragdenstaat.de", password=data["new_password2"])
    assert ok


@pytest.mark.django_db
def test_send_reset_password_link(world, client):
    mail.outbox = []
    response = client.get(reverse("account-send_reset_password_link"))
    assert response.status_code == 405
    ok = client.login(email="info@fragdenstaat.de", password="froide")
    data = {"pwreset-email": "unknown@example.com"}
    response = client.post(reverse("account-send_reset_password_link"))
    assert response.status_code == 302
    assert len(mail.outbox) == 0
    client.logout()
    response = client.post(reverse("account-send_reset_password_link"), data)
    assert response.status_code == 302
    assert len(mail.outbox) == 0
    data["pwreset-email"] = "info@fragdenstaat.de"
    response = client.post(reverse("account-send_reset_password_link"), data)
    assert response.status_code == 302
    message = mail.outbox[0]
    match = re.search(r"/account/reset/([^/]+)/([^/]+)/", message.body)
    uidb64 = match.group(1)
    token = match.group(2)
    response = client.get(
        reverse(
            "account-password_reset_confirm",
            kwargs={"uidb64": uidb64, "token": "2y1-d0b8c8b186fdc63ccc6"},
        )
    )
    assert response.status_code == 200
    assert not response.context["validlink"]
    response = client.get(
        reverse(
            "account-password_reset_confirm",
            kwargs={"uidb64": uidb64, "token": token},
        ),
        follow=True,
    )
    assert response.status_code == 200
    assert response.context["validlink"]
    data = {"new_password1": "froide4froide5", "new_password2": "froide4froide5"}
    response = client.post(response.wsgi_request.path, data)
    assert response.status_code == 302
    # we are already logged in after redirect
    response = client.get(reverse("account-requests"))
    assert response.status_code == 200
    client.logout()
    ok = client.login(email="info@fragdenstaat.de", password="froide4froide5")
    assert ok


@pytest.mark.django_db
def test_next_password_reset(world, client):
    mail.outbox = []
    mes = FoiMessage.objects.all()[0]
    url = mes.get_absolute_url()
    data = {"pwreset-email": "info@fragdenstaat.de", "next": url}
    response = client.post(reverse("account-send_reset_password_link"), data)
    assert response.status_code == 302
    assert response.url.endswith(url)
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
    assert response.url.endswith(url)


@pytest.mark.django_db
def test_private_name(world, client):
    user = User.objects.get(username="dummy")
    user.private = True
    user.save()
    client.login(email="dummy@example.org", password="froide")
    pb = PublicBody.objects.all()[0]
    post = {
        "subject": "Request - Private name",
        "body": "This is a test body",
        "public": True,
        "publicbody": pb.pk,
        "law": pb.default_law.pk,
    }
    response = client.post(
        reverse("foirequest-make_request", kwargs={"publicbody_slug": pb.slug}),
        post,
    )
    assert response.status_code == 302
    req = FoiRequest.objects.filter(user=user, public_body=pb).order_by("-id")[0]
    client.logout()  # log out to remove Account link
    response = client.get(reverse("foirequest-show", kwargs={"slug": req.slug}))
    assert response.status_code == 200
    assert user.get_full_name().encode("utf-8") not in response.content
    assert user.last_name.encode("utf-8") not in response.content
    assert "" == user.get_absolute_url()


@pytest.mark.django_db
def test_change_user(world, client):
    data = {}
    response = client.post(reverse("account-change_user"), data)
    assert response.status_code == 302
    assert reverse("account-login") in response["Location"]
    assert "?next=" in response["Location"]
    ok = client.login(email="info@fragdenstaat.de", password="froide")
    assert ok
    response = client.post(reverse("account-change_user"), data)
    assert response.status_code == 302
    data["address"] = ""
    response = client.post(reverse("account-change_user"), data)
    assert response.status_code == 302
    data["address"] = "Some Value"
    response = client.post(reverse("account-change_user"), data)
    assert response.status_code == 302
    user = User.objects.get(username="sw")
    assert user.address == data["address"]


@pytest.mark.django_db
def test_go(world, client):
    user = User.objects.get(username="dummy")
    other_user = User.objects.get(username="sw")
    super_user = User.objects.get(username="supersw")

    # test url is not cached and does not cause 404
    test_url = reverse("foirequest-make_request")
    login_url = reverse("account-login")

    # Super users are not logged in
    super_autologin = super_user.get_autologin_url()
    assert super_autologin.startswith("http://")
    response = client.post(super_autologin)
    assert response.status_code == 200
    assert response.context["user"].is_anonymous

    # Try logging in via link: success
    autologin = user.get_autologin_url(test_url)
    assert autologin.startswith("http://")
    response = client.get(autologin)
    assert response.status_code == 200
    response = client.post(autologin)
    assert response.status_code == 302
    response = client.get(test_url)
    assert response.status_code == 200
    assert response.context["user"] == user
    assert response.context["user"].is_authenticated
    client.logout()

    # Try logging in again, should not work
    response = client.get(autologin)
    assert response.status_code == 200
    response = client.post(autologin)
    assert response.status_code == 302
    response = client.get(test_url)
    assert response.status_code == 200
    assert not response.context["user"] == user

    # Try logging in via link: other user is authenticated
    ok = client.login(email="info@fragdenstaat.de", password="froide")
    assert ok
    autologin = user.get_autologin_url(test_url)
    response = client.post(autologin)
    assert response.status_code == 302
    response = client.get(test_url)
    assert response.status_code == 200
    assert response.context["user"] == other_user
    assert response.context["user"].is_authenticated
    client.logout()

    # Try logging in via link: user is blocked
    autologin = user.get_autologin_url(test_url)
    user.is_blocked = True
    user.save()
    response = client.post(autologin)
    assert response.status_code == 302
    assert response["Location"].startswith(login_url)
    response = client.get(test_url)
    assert response.context["user"].is_anonymous

    # Try logging in via link: wrong user id
    autologin = reverse(
        "account-go", kwargs={"user_id": "80000", "token": "a" * 32, "url": test_url}
    )
    response = client.post(autologin)
    assert response.status_code == 302
    assert response["Location"].startswith(login_url)
    response = client.get(test_url)
    assert response.context["user"].is_anonymous
    user.is_active = True
    user.save()

    # Try logging in via link: wrong secret
    autologin = reverse(
        "account-go",
        kwargs={"user_id": str(user.id), "token": "a" * 32, "url": test_url},
    )
    response = client.post(autologin)
    assert response.status_code == 302
    assert response["Location"].startswith(login_url)
    response = client.get(test_url)
    assert response.context["user"].is_anonymous

    # Try logging in via link: wrong secret but nologin tag
    autologin = reverse(
        "account-go",
        kwargs={"user_id": str(user.id), "token": "a" * 32, "url": test_url},
    )
    response = client.get(autologin + "?nologin=1")
    assert response.context["nologin"] == "1"
    assert '<input type="hidden" name="nologin" value="1">' in response.text
    response = client.post(autologin, {"nologin": "1"})
    assert response.status_code == 302
    assert response["Location"].startswith(test_url)
    response = client.get(test_url)
    assert response.context["user"].is_anonymous


@pytest.mark.django_db
def test_go_redirect_without_loop(client):
    user = UserFactory.create()
    # Foirequest is private
    foirequest = factories.FoiRequestFactory.create(user=user, visibility=1)

    # Super users are not logged in
    next_url = foirequest.get_absolute_short_url()
    autologin_url = user.get_autologin_url(next_url)

    # Invalidate access token to prevent login
    AccessToken.objects.filter(user=user).delete()

    # Get autologin url
    response = client.get(autologin_url)
    form_action = response.context["form_action"]
    next_url = response.context["next"]
    # Post to autologin url
    response = client.post(form_action, {"next": next_url})
    assert response.status_code == 302
    qs = urlencode({"next": next_url}, safe="/")
    assert response["Location"] == f"{reverse(settings.LOGIN_URL)}?{qs}"


@pytest.mark.django_db
def test_profile_page(world, client):
    user = User.objects.get(username="sw")
    response = client.get(reverse("account-profile", kwargs={"slug": user.username}))
    assert response.status_code == 200
    user2 = factories.UserFactory.create()
    user2.private = True
    user2.save()
    response = client.get(reverse("account-profile", kwargs={"slug": user2.username}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_change_email(world, client):
    mail.outbox = []
    new_email = "newemail@example.com"
    user = User.objects.get(username="sw")

    response = client.post(
        reverse("account-change_user"),
        {
            "address": "Test",
            "email": "not-email",
        },
    )
    assert response.status_code == 302
    assert reverse("account-login") in response["Location"]
    assert "?next=" in response["Location"]
    assert len(mail.outbox) == 0

    client.login(email="info@fragdenstaat.de", password="froide")

    response = client.post(
        reverse("account-change_user"),
        {
            "address": "Test",
            "email": "not-email",
        },
    )
    assert response.status_code == 400
    assert len(mail.outbox) == 0

    response = client.post(
        reverse("account-change_user"), {"address": "Test", "email": user.email}
    )
    assert response.status_code == 302
    assert len(mail.outbox) == 0
    response = client.post(
        reverse("account-change_user"),
        {
            "address": "Test",
            "email": new_email,
        },
    )
    assert response.status_code == 302
    user = User.objects.get(pk=user.pk)
    assert not user.email == new_email
    assert len(mail.outbox) == 1

    url_kwargs = {"user_id": user.pk, "secret": "f" * 32, "email": new_email}
    url = "%s?%s" % (reverse("account-change_email"), urlencode(url_kwargs))
    response = client.get(url)
    assert response.status_code == 302
    user = User.objects.get(pk=user.pk)
    assert not user.email == new_email

    email = mail.outbox[0]
    assert email.to[0] == new_email
    match = re.search(r"https?\://[^/]+(/.*)", email.body)
    url = match.group(1)

    bad_url = url.replace("user_id=%d" % user.pk, "user_id=999999")
    response = client.get(bad_url)
    assert response.status_code == 302
    user = User.objects.get(pk=user.pk)
    assert not user.email == new_email

    response = client.get(url)
    assert response.status_code == 302
    user = User.objects.get(pk=user.pk)
    assert user.email == new_email


@pytest.mark.django_db
def test_account_delete(world, client):
    response = client.get(reverse("account-settings"))
    assert response.status_code == 302
    response = client.post(
        reverse("account-delete_account"),
        {"password": "froide", "confirmation": "Freedom of Information Act"},
    )
    assert response.status_code == 302
    assert reverse("account-login") in response["Location"]
    assert "?next=" in response["Location"]

    user = User.objects.get(username="sw")
    client.login(email="info@fragdenstaat.de", password="froide")

    response = client.get(reverse("account-settings"))
    assert response.status_code == 200

    response = client.post(
        reverse("account-delete_account"),
        {"password": "bad-password", "confirmation": "Freedom of Information Act"},
    )
    assert response.status_code == 400

    response = client.post(
        reverse("account-delete_account"),
        {"password": "froide", "confirmation": "Strange Information Act"},
    )
    assert response.status_code == 400

    req = user.foirequest_set.all()[0]
    assert not req.closed
    messages = req.messages
    mes = messages[1]
    mes.recipient = user.get_full_name()
    mes.plaintext = user.first_name
    mes.save()

    with mock.patch(
        "froide.foirequest.utils.delete_foirequest_emails_from_imap"
    ) as mock_func:
        mock_func.return_value = 30
        response = client.post(
            reverse("account-delete_account"),
            {"password": "froide", "confirmation": "Freedom of Information Act"},
        )
    assert response.status_code == 302

    user = User.objects.get(pk=user.pk)
    assert user.first_name == ""
    assert user.last_name == ""
    assert user.email is None
    assert user.username == "u%s" % user.pk
    assert user.address == ""
    assert user.organization_name == ""
    assert user.organization_url == ""
    assert user.private
    assert user.is_deleted
    assert user.date_left is not None

    req = user.foirequest_set.all()[0]
    assert req.closed
    messages = req.messages
    mes = messages[1]
    assert mes.plaintext == "<information-removed>"


@pytest.mark.django_db
def test_merge_account(world, foi_request_factory, foi_request_follower_factory):
    user = User.objects.get(username="dummy")
    req = FoiRequest.objects.all().first()
    new_req = foi_request_factory()
    old_user = req.user
    foi_request_follower_factory(user=user, content_object=new_req)
    foi_request_follower_factory(user=old_user, content_object=new_req)
    mes = req.messages
    assert mes[0].sender_user == old_user
    merge_accounts(old_user, user)

    assert 1 == FoiRequestFollower.objects.filter(content_object=new_req).count()
    req = FoiRequest.objects.get(pk=req.pk)
    mes = req.messages
    assert req.user == user
    assert mes[0].sender_user == user


@pytest.mark.django_db
def test_send_mass_mail(world):
    user_count = User.objects.all().count()
    mail.outbox = []
    command = Command()
    subject, content = "Test", "Testing-Content"
    list(command.send_mail(subject, content))
    assert len(mail.outbox) == user_count


@pytest.mark.django_db
def test_signup_blocklisted(world, client):
    mail.outbox = []
    post = {
        "first_name": "Horst",
        "last_name": "Porst",
        "terms": "on",
        "private": True,
        "user_email": "horst.porst@example.com",
        "time": (datetime.now(timezone.utc) - timedelta(seconds=30)).timestamp(),
    }

    AccountBlocklist.objects.create(name="Test", email="horst\\.porst.*@example.com$")

    response = client.post(reverse("account-signup"), post)
    assert response.status_code == 302
    user = User.objects.get(email=post["user_email"])
    assert user.is_blocked


@pytest.mark.django_db
def test_send_mail(world, rf):
    user = User.objects.get(username="sw")
    user.is_superuser = True
    to_user = User.objects.first()
    users = User.objects.filter(id__in=[to_user.id])

    admin_site = AdminSite()
    user_admin = UserAdmin(User, admin_site)

    req = rf.post("/", {})
    req.user = user
    result = user_admin.send_mail(req, users)
    assert result.status_code == 200

    req = rf.post("/", {"subject": "Test", "body": "^{name}|{first_name}|{last_name}|"})
    req.user = user
    req._messages = default_storage(req)
    mail.outbox = []

    result = user_admin.send_mail(req, users)
    assert result is None
    assert len(mail.outbox) == users.count()
    message = mail.outbox[0]
    user = users[0]
    assert "|%s|" % user.first_name in message.body
    assert "|%s|" % user.last_name in message.body
    assert "^%s|" % user.get_full_name() in message.body


@pytest.mark.django_db
def test_email_case_insensitive_search():
    user = User.objects.create(email="Hacker@example.com")
    user2 = User.objects.get(email="hacker@example.com")
    assert user == user2


@pytest.mark.django_db
def test_email_case_insensitive_unique():
    User.objects.create(email="Hacker@example.com")
    msg = 'duplicate key value violates unique constraint "account_user_username_key"'
    with pytest.raises(IntegrityError, match=msg):
        User.objects.create(email="hacker@example.com")


@pytest.mark.django_db
def test_multipart_name_redaction():
    user = User.objects.create(
        first_name="Alex", last_name="Random Example", private=True
    )
    account_service = AccountService(user)
    name = "Reply-Alex-Random-Example.pdf"
    repl = "NAME"
    redacted_name = account_service.apply_name_redaction(name, repl)
    assert redacted_name == "Reply-NAME-NAME-NAME.pdf"
