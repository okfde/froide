import re
from datetime import datetime, timedelta
from unittest import mock
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage import default_storage
from django.core import mail
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import escape

from froide.foirequest.models import FoiMessage, FoiRequest
from froide.foirequest.tests import factories
from froide.publicbody.models import PublicBody

from ..admin import UserAdmin
from ..models import AccountBlocklist
from ..services import AccountService
from ..utils import merge_accounts

User = get_user_model()

SPAM_ENABLED_CONFIG = dict(settings.FROIDE_CONFIG)
SPAM_ENABLED_CONFIG["spam_protection"] = True


class AccountTest(TestCase):
    def setUp(self):
        factories.make_world()

    def assertForbidden(self, response: HttpResponse):
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account-login"), response["Location"])
        self.assertIn("?next=", response["Location"])

    def test_account_page(self):
        ok = self.client.login(email="info@fragdenstaat.de", password="wrong")
        self.assertFalse(ok)
        ok = self.client.login(email="info@fragdenstaat.de", password="froide")
        self.assertTrue(ok)
        response = self.client.get(reverse("account-requests"))
        self.assertEqual(response.status_code, 200)

    def test_account_drafts(self):
        response = self.client.get(reverse("account-drafts"))
        self.assertEqual(response.status_code, 302)
        ok = self.client.login(email="info@fragdenstaat.de", password="froide")
        self.assertTrue(ok)

        user = User.objects.get(email="info@fragdenstaat.de")
        draft = factories.RequestDraftFactory.create(user=user)

        response = self.client.get(reverse("account-drafts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, draft.subject)
        self.assertContains(response, escape(draft.get_absolute_url()))

    def test_account_following(self):
        response = self.client.get(reverse("account-following"))
        self.assertEqual(response.status_code, 302)
        ok = self.client.login(email="info@fragdenstaat.de", password="froide")
        self.assertTrue(ok)

        response = self.client.get(reverse("account-following"))
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        self.client.logout()
        response = self.client.get(reverse("account-requests"))
        self.assertEqual(response.status_code, 302)
        self.client.get(reverse("account-login"))
        response = self.client.post(
            reverse("account-login"),
            {"username": "doesnt@exist.com", "password": "foobar"},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("account-login"),
            {"username": "info@fragdenstaat.de", "password": "dummy"},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("account-login"),
            {"username": "info@fragdenstaat.de", "password": "froide"},
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("account-requests"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("account-login"),
            {"username": "info@fragdenstaat.de", "password": "froide"},
        )
        # already logged in, login again gives 302
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account-show"), response.url)
        # logout only via POST
        response = self.client.get(reverse("account-logout"))
        self.assertEqual(response.status_code, 405)
        response = self.client.post(reverse("account-logout"))
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(email="info@fragdenstaat.de")
        user.is_active = False
        user.save()
        self.client.logout()
        response = self.client.post(
            reverse("account-login"),
            {"email": "info@fragdenstaat.de", "password": "froide"},
        )
        # inactive users can't login via password
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("account-requests"))
        self.assertEqual(response.status_code, 302)

    def test_signup(self):
        froide_config = settings.FROIDE_CONFIG
        mail.outbox = []
        post = {
            "first_name": "Horst",
            "last_name": "Porst",
            "terms": "on",
            "user_email": "horst.porst",
            "time": (datetime.utcnow() - timedelta(seconds=30)).timestamp(),
        }
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(reverse("account-signup"), post)
        self.assertTrue(response.status_code, 302)
        self.assertTrue(response.url, "/")

        self.assertEqual(len(mail.outbox), 0)
        self.client.logout()
        response = self.client.post(reverse("account-signup"), post)
        self.assertEqual(response.status_code, 200)
        post["user_email"] = "horst.porst@example.com"
        post["address"] = "MyOwnPrivateStree 5\n31415 Pi-Ville"

        with self.settings(FROIDE_CONFIG=froide_config):
            response = self.client.post(reverse("account-signup"), post)

        self.assertEqual(response.status_code, 302)
        new_account_url = reverse("account-new")
        self.assertIn(new_account_url, response.url)

        user = User.objects.get(email=post["user_email"])
        self.assertEqual(user.first_name, post["first_name"])
        self.assertEqual(user.last_name, post["last_name"])
        self.assertEqual(user.address, post["address"])
        self.assertEqual(mail.outbox[0].to[0], post["user_email"])

        # sign up with email that is not confirmed
        response = self.client.post(reverse("account-signup"), post)
        self.assertTrue(response.status_code, 200)

        # sign up with email that is confirmed
        message = mail.outbox[0]
        match = re.search(r"/%d/(\w+)/" % user.pk, message.body)
        response = self.client.get(
            reverse(
                "account-confirm", kwargs={"user_id": user.pk, "secret": match.group(1)}
            )
        )
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        user = User.objects.get(id=user.pk)
        self.assertTrue(user.is_active)
        response = self.client.post(reverse("account-signup"), post)
        self.assertTrue(response.status_code, 200)

    def test_overlong_name_signup(self):
        post = {
            "first_name": "Horst" * 6 + "a",
            "last_name": "Porst" * 6,
            "terms": "on",
            "user_email": "horst.porst@example.com",
            "address": "MyOwnPrivateStree 5\n31415 Pi-Ville",
            "time": (datetime.utcnow() - timedelta(seconds=30)).timestamp(),
        }
        self.client.logout()
        response = self.client.post(reverse("account-signup"), post)
        self.assertEqual(response.status_code, 200)
        post["first_name"] = post["first_name"][:-1]
        response = self.client.post(reverse("account-signup"), post)
        self.assertEqual(response.status_code, 302)

    @override_settings(FROIDE_CONFIG=SPAM_ENABLED_CONFIG)
    def test_signup_too_fast(self):
        post = {
            "first_name": "Horst",
            "last_name": "Porst",
            "terms": "on",
            "user_email": "horst.porst@example.com",
            "address": "MyOwnPrivateStree 5\n31415 Pi-Ville",
            # Signup in less than 5 seconds
            "time": (datetime.utcnow() - timedelta(seconds=3)).timestamp(),
        }
        self.client.logout()
        response = self.client.post(reverse("account-signup"), post)
        self.assertEqual(response.status_code, 200)

    def test_signup_same_name(self):
        self.client.logout()
        post = {
            "first_name": "Horst",
            "last_name": "Porst",
            "terms": "on",
            "user_email": "horst.porst@example.com",
            "address": "MyOwnPrivateStree 5\n31415 Pi-Ville",
            "time": (datetime.utcnow() - timedelta(seconds=30)).timestamp(),
        }
        response = self.client.post(reverse("account-signup"), post)
        self.assertEqual(response.status_code, 302)
        post["user_email"] = "horst.porst2@example.com"
        response = self.client.post(reverse("account-signup"), post)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="horst.porst2@example.com")
        self.assertEqual(user.username, "h.porst_1")

    def test_confirmation_process(self):
        self.client.logout()
        user, user_created = AccountService.create_user(
            first_name="Stefan",
            last_name="Wehrmeyer",
            user_email="sw@example.com",
            address="SomeRandomAddress\n11234 Bern",
            private=True,
        )
        AccountService(user).send_confirmation_mail()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        match = re.search(r"/%d/(\w+)/" % user.pk, message.body)
        response = self.client.get(
            reverse(
                "account-confirm", kwargs={"user_id": user.pk, "secret": match.group(1)}
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account-show"), response.url)
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("account-requests"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("account-confirm", kwargs={"user_id": user.pk, "secret": "a" * 32})
        )
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        response = self.client.get(
            reverse(
                "account-confirm", kwargs={"user_id": user.pk, "secret": match.group(1)}
            )
        )
        # user is already active, link does not exist
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("account-login"))
        # deactivate user
        user = User.objects.get(pk=user.pk)
        user.is_active = False
        # set last_login back artificially so it's not the same
        # as in secret link
        user.last_login = user.last_login - timedelta(seconds=10)
        user.save()
        response = self.client.get(
            reverse(
                "account-confirm", kwargs={"user_id": user.pk, "secret": match.group(1)}
            )
        )
        # user is inactive, but link was already used
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account-login"), response.url)

    def test_next_link_login(self):
        mes = FoiMessage.objects.all()[0]
        url = mes.get_absolute_url()
        enc_url = url.replace("#", "%23")  # FIXME: fake uri encode
        response = self.client.get(reverse("account-login") + "?next=%s" % enc_url)
        # occurences in hidden inputs of login, signup and forgotten password
        self.assertTrue(response.content.decode("utf-8").count(url), 3)
        response = self.client.post(
            reverse("account-login"),
            {"username": "info@fragdenstaat.de", "next": url, "password": "froide"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(url))

    def test_next_link_signup(self):
        self.client.logout()
        mail.outbox = []
        mes = FoiMessage.objects.all()[0]
        url = mes.get_absolute_url()
        post = {
            "first_name": "Horst",
            "last_name": "Porst",
            "terms": "on",
            "user_email": "horst.porst@example.com",
            "address": "MyOwnPrivateStree 5\n31415 Pi-Ville",
            "next": url,
            "time": (datetime.utcnow() - timedelta(seconds=30)).timestamp(),
        }
        response = self.client.post(reverse("account-signup"), post)
        self.assertEqual(response.status_code, 302)
        new_account_url = reverse("account-new")
        self.assertIn(new_account_url, response.url)

        user = User.objects.get(email=post["user_email"])
        message = mail.outbox[0]
        match = re.search(r"/%d/(\w+)/" % user.pk, message.body)
        response = self.client.get(
            reverse(
                "account-confirm", kwargs={"user_id": user.pk, "secret": match.group(1)}
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(url))

    def test_change_password(self):
        response = self.client.get(reverse("account-change_password"))
        self.assertEqual(response.status_code, 405)
        data = {"new_password1": "froide1froide2", "new_password2": "froide1froide3"}
        response = self.client.post(reverse("account-change_password"), data)
        self.assertEqual(response.status_code, 302)
        self.assertForbidden(response)
        ok = self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(reverse("account-change_password"), data)
        self.assertEqual(response.status_code, 400)
        data["new_password2"] = "froide1froide2"
        response = self.client.post(reverse("account-change_password"), data)
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        ok = self.client.login(email="info@fragdenstaat.de", password="froide")
        self.assertFalse(ok)
        ok = self.client.login(
            email="info@fragdenstaat.de", password=data["new_password2"]
        )
        self.assertTrue(ok)

    def test_send_reset_password_link(self):
        mail.outbox = []
        response = self.client.get(reverse("account-send_reset_password_link"))
        self.assertEqual(response.status_code, 405)
        ok = self.client.login(email="info@fragdenstaat.de", password="froide")
        data = {"pwreset-email": "unknown@example.com"}
        response = self.client.post(reverse("account-send_reset_password_link"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
        self.client.logout()
        response = self.client.post(reverse("account-send_reset_password_link"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
        data["pwreset-email"] = "info@fragdenstaat.de"
        response = self.client.post(reverse("account-send_reset_password_link"), data)
        self.assertEqual(response.status_code, 302)
        message = mail.outbox[0]
        match = re.search(r"/account/reset/([^/]+)/([^/]+)/", message.body)
        uidb64 = match.group(1)
        token = match.group(2)
        response = self.client.get(
            reverse(
                "account-password_reset_confirm",
                kwargs={"uidb64": uidb64, "token": "2y1-d0b8c8b186fdc63ccc6"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["validlink"])
        response = self.client.get(
            reverse(
                "account-password_reset_confirm",
                kwargs={"uidb64": uidb64, "token": token},
            ),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["validlink"])
        data = {"new_password1": "froide4froide5", "new_password2": "froide4froide5"}
        response = self.client.post(response.wsgi_request.path, data)
        self.assertEqual(response.status_code, 302)
        # we are already logged in after redirect
        response = self.client.get(reverse("account-requests"))
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        ok = self.client.login(email="info@fragdenstaat.de", password="froide4froide5")
        self.assertTrue(ok)

    def test_next_password_reset(self):
        mail.outbox = []
        mes = FoiMessage.objects.all()[0]
        url = mes.get_absolute_url()
        data = {"pwreset-email": "info@fragdenstaat.de", "next": url}
        response = self.client.post(reverse("account-send_reset_password_link"), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(url))
        message = mail.outbox[0]
        match = re.search(r"/account/reset/([^/]+)/([^/]+)/", message.body)
        uidb64 = match.group(1)
        token = match.group(2)
        response = self.client.get(
            reverse(
                "account-password_reset_confirm",
                kwargs={"uidb64": uidb64, "token": token},
            ),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        data = {"new_password1": "froide4froide5", "new_password2": "froide4froide5"}
        response = self.client.post(response.wsgi_request.path, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(url))

    def test_private_name(self):
        user = User.objects.get(username="dummy")
        user.private = True
        user.save()
        self.client.login(email="dummy@example.org", password="froide")
        pb = PublicBody.objects.all()[0]
        post = {
            "subject": "Request - Private name",
            "body": "This is a test body",
            "public": "on",
            "publicbody": pb.pk,
            "law": pb.default_law.pk,
        }
        response = self.client.post(
            reverse("foirequest-make_request", kwargs={"publicbody_slug": pb.slug}),
            post,
        )
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.filter(user=user, public_body=pb).order_by("-id")[0]
        self.client.logout()  # log out to remove Account link
        response = self.client.get(
            reverse("foirequest-show", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(user.get_full_name().encode("utf-8"), response.content)
        self.assertNotIn(user.last_name.encode("utf-8"), response.content)
        self.assertEqual("", user.get_absolute_url())

    def test_change_user(self):
        data = {}
        response = self.client.post(reverse("account-change_user"), data)
        self.assertEqual(response.status_code, 302)
        self.assertForbidden(response)

        ok = self.client.login(email="info@fragdenstaat.de", password="froide")
        self.assertTrue(ok)
        response = self.client.post(reverse("account-change_user"), data)
        self.assertEqual(response.status_code, 302)
        data["address"] = ""
        response = self.client.post(reverse("account-change_user"), data)
        self.assertEqual(response.status_code, 302)
        data["address"] = "Some Value"
        response = self.client.post(reverse("account-change_user"), data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="sw")
        self.assertEqual(user.address, data["address"])

    def test_go(self):
        user = User.objects.get(username="dummy")
        other_user = User.objects.get(username="sw")
        super_user = User.objects.get(username="supersw")

        # test url is not cached and does not cause 404
        test_url = reverse("foirequest-make_request")
        login_url = reverse("account-login")

        # Super users are not logged in
        super_autologin = super_user.get_autologin_url()
        self.assertTrue(super_autologin.startswith("http://"))
        response = self.client.post(super_autologin)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_anonymous)

        # Try logging in via link: success
        autologin = user.get_autologin_url(test_url)
        self.assertTrue(autologin.startswith("http://"))
        response = self.client.get(autologin)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(autologin)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"], user)
        self.assertTrue(response.context["user"].is_authenticated)
        self.client.logout()

        # Try logging in again, should not work
        response = self.client.get(autologin)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(autologin)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.context["user"], user)

        # Try logging in via link: other user is authenticated
        ok = self.client.login(email="info@fragdenstaat.de", password="froide")
        self.assertTrue(ok)
        autologin = user.get_autologin_url(test_url)
        response = self.client.post(autologin)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"], other_user)
        self.assertTrue(response.context["user"].is_authenticated)
        self.client.logout()

        # Try logging in via link: user is blocked
        autologin = user.get_autologin_url(test_url)
        user.is_blocked = True
        user.save()
        response = self.client.post(autologin)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(login_url))
        response = self.client.get(test_url)
        self.assertTrue(response.context["user"].is_anonymous)

        # Try logging in via link: wrong user id
        autologin = reverse(
            "account-go", kwargs=dict(user_id="80000", token="a" * 32, url=test_url)
        )
        response = self.client.post(autologin)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(login_url))
        response = self.client.get(test_url)
        self.assertTrue(response.context["user"].is_anonymous)
        user.is_active = True
        user.save()

        # Try logging in via link: wrong secret
        autologin = reverse(
            "account-go",
            kwargs=dict(user_id=str(user.id), token="a" * 32, url=test_url),
        )
        response = self.client.post(autologin)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(login_url))
        response = self.client.get(test_url)
        self.assertTrue(response.context["user"].is_anonymous)

    def test_profile_page(self):
        user = User.objects.get(username="sw")
        response = self.client.get(
            reverse("account-profile", kwargs={"slug": user.username})
        )
        self.assertEqual(response.status_code, 200)
        user2 = factories.UserFactory.create()
        user2.private = True
        user2.save()
        response = self.client.get(
            reverse("account-profile", kwargs={"slug": user2.username})
        )
        self.assertEqual(response.status_code, 404)

    def test_change_email(self):
        mail.outbox = []
        new_email = "newemail@example.com"
        user = User.objects.get(username="sw")

        response = self.client.post(
            reverse("account-change_user"),
            {
                "address": "Test",
                "email": "not-email",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertForbidden(response)
        self.assertEqual(len(mail.outbox), 0)

        self.client.login(email="info@fragdenstaat.de", password="froide")

        response = self.client.post(
            reverse("account-change_user"),
            {
                "address": "Test",
                "email": "not-email",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

        response = self.client.post(
            reverse("account-change_user"), {"address": "Test", "email": user.email}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.post(
            reverse("account-change_user"),
            {
                "address": "Test",
                "email": new_email,
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(pk=user.pk)
        self.assertNotEqual(user.email, new_email)
        self.assertEqual(len(mail.outbox), 1)

        url_kwargs = {"user_id": user.pk, "secret": "f" * 32, "email": new_email}
        url = "%s?%s" % (reverse("account-change_email"), urlencode(url_kwargs))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(pk=user.pk)
        self.assertNotEqual(user.email, new_email)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], new_email)
        match = re.search(r"https?\://[^/]+(/.*)", email.body)
        url = match.group(1)

        bad_url = url.replace("user_id=%d" % user.pk, "user_id=999999")
        response = self.client.get(bad_url)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(pk=user.pk)
        self.assertNotEqual(user.email, new_email)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(pk=user.pk)
        self.assertEqual(user.email, new_email)

    def test_account_delete(self):
        response = self.client.get(reverse("account-settings"))
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            reverse("account-delete_account"),
            {"password": "froide", "confirmation": "Freedom of Information Act"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertForbidden(response)

        user = User.objects.get(username="sw")
        self.client.login(email="info@fragdenstaat.de", password="froide")

        response = self.client.get(reverse("account-settings"))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("account-delete_account"),
            {"password": "bad-password", "confirmation": "Freedom of Information Act"},
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            reverse("account-delete_account"),
            {"password": "froide", "confirmation": "Strange Information Act"},
        )
        self.assertEqual(response.status_code, 400)

        req = user.foirequest_set.all()[0]
        self.assertFalse(req.closed)
        messages = req.messages
        mes = messages[1]
        mes.recipient = user.get_full_name()
        mes.plaintext = user.first_name
        mes.save()

        with mock.patch(
            "froide.foirequest.utils.delete_foirequest_emails_from_imap"
        ) as mock_func:
            mock_func.return_value = 30
            response = self.client.post(
                reverse("account-delete_account"),
                {"password": "froide", "confirmation": "Freedom of Information Act"},
            )
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(pk=user.pk)
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")
        self.assertIsNone(user.email)
        self.assertEqual(user.username, "u%s" % user.pk)
        self.assertEqual(user.address, "")
        self.assertEqual(user.organization_name, "")
        self.assertEqual(user.organization_url, "")
        self.assertTrue(user.private)
        self.assertTrue(user.is_deleted)
        self.assertIsNotNone(user.date_left)

        req = user.foirequest_set.all()[0]
        self.assertTrue(req.closed)
        messages = req.messages
        mes = messages[1]
        self.assertEqual(mes.plaintext, "<information-removed>")

    def test_merge_account(self):
        from froide.foirequestfollower.models import FoiRequestFollower
        from froide.foirequestfollower.tests import FoiRequestFollowerFactory

        new_user = factories.UserFactory.create()
        req = FoiRequest.objects.all()[0]
        new_req = factories.FoiRequestFactory.create()
        old_user = req.user
        FoiRequestFollowerFactory.create(user=new_user, request=new_req)
        FoiRequestFollowerFactory.create(user=old_user, request=new_req)
        mes = req.messages
        self.assertEqual(mes[0].sender_user, old_user)
        merge_accounts(old_user, new_user)

        self.assertEqual(1, FoiRequestFollower.objects.filter(request=new_req).count())
        req = FoiRequest.objects.get(pk=req.pk)
        mes = req.messages
        self.assertEqual(req.user, new_user)
        self.assertEqual(mes[0].sender_user, new_user)

    def test_send_mass_mail(self):
        from froide.account.management.commands.send_mass_mail import Command

        user_count = User.objects.all().count()
        mail.outbox = []
        command = Command()
        subject, content = "Test", "Testing-Content"
        list(command.send_mail(subject, content))
        self.assertEqual(len(mail.outbox), user_count)

    def test_signup_blocklisted(self):
        froide_config = settings.FROIDE_CONFIG
        mail.outbox = []
        post = {
            "first_name": "Horst",
            "last_name": "Porst",
            "terms": "on",
            "user_email": "horst.porst@example.com",
            "time": (datetime.utcnow() - timedelta(seconds=30)).timestamp(),
        }

        AccountBlocklist.objects.create(
            name="Test", email="horst\\.porst.*@example.com$"
        )

        with self.settings(FROIDE_CONFIG=froide_config):
            response = self.client.post(reverse("account-signup"), post)

        self.assertEqual(response.status_code, 302)

        user = User.objects.get(email=post["user_email"])
        self.assertTrue(user.is_blocked)


class AdminActionTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()
        self.admin_site = AdminSite()
        self.user_admin = UserAdmin(User, self.admin_site)
        self.factory = RequestFactory()
        self.user = User.objects.get(username="sw")
        self.user.is_superuser = True

    def test_send_mail(self):
        users = User.objects.all()[:1]

        req = self.factory.post("/", {})
        req.user = self.user
        result = self.user_admin.send_mail(req, users)
        self.assertEqual(result.status_code, 200)

        req = self.factory.post(
            "/", {"subject": "Test", "body": "^{name}|{first_name}|{last_name}|"}
        )
        req.user = self.user
        req._messages = default_storage(req)
        mail.outbox = []

        result = self.user_admin.send_mail(req, users)
        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), users.count())
        message = mail.outbox[0]
        user = users[0]
        self.assertIn("|%s|" % user.first_name, message.body)
        self.assertIn("|%s|" % user.last_name, message.body)
        self.assertIn("^%s|" % user.get_full_name(), message.body)
