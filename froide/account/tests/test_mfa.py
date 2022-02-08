import re
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from mfa.models import MFAKey

from froide.foirequest.tests import factories

User = get_user_model()


class MFATest(TestCase):
    def setUp(self):
        factories.make_world()
        self.test_user = User.objects.get(username="dummy")
        MFAKey.objects.create(user=self.test_user, method="recovery")

    def test_mfa_after_password(self):
        response = self.client.post(
            reverse("account-login"),
            data={"username": self.test_user.email, "password": "froide"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("mfa:auth", kwargs={"method": "recovery"}), response["Location"]
        )
        # not logged in
        response = self.client.get(reverse("account-requests"))
        self.assertEqual(response.status_code, 302)

    def test_recently_authenticated(self):
        self.client.login(email=self.test_user.email, password="froide")
        # oauth app list is protected by recently authenticated wrapper

        response = self.client.get(reverse("oauth2_provider:list"))
        # Works right afer login
        self.assertEqual(response.status_code, 200)

        # Patch recent auth duration to negative
        with mock.patch(
            "froide.account.auth.RECENT_AUTH_DURATION", -timedelta(seconds=1)
        ):
            response = self.client.get(reverse("oauth2_provider:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account-reauth"), response["Location"])

    def test_password_reset_mfa_no_login(self):
        data = {"pwreset-email": self.test_user.email}
        response = self.client.post(reverse("account-send_reset_password_link"), data)
        self.assertEqual(response.status_code, 302)
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
        self.assertIn(
            reverse("mfa:auth", kwargs={"method": "recovery"}), response["Location"]
        )
        # We are not logged in
        response = self.client.get(reverse("account-requests"))
        self.assertEqual(response.status_code, 302)

    def test_go_with_mfa(self):
        test_url = reverse("account-requests")

        # Try logging in via link: success
        autologin = self.test_user.get_autologin_url(test_url)
        response = self.client.get(autologin)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(autologin)
        self.assertEqual(response.status_code, 302)

        self.assertIn(
            reverse("mfa:auth", kwargs={"method": "recovery"}), response["Location"]
        )

        # We are not logged in
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 302)

    def test_admin_login_url(self):
        admin_login_url = reverse("admin:login")

        response = self.client.get(admin_login_url)
        # Admin login page redirects to account login page
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account-login"), response["Location"])
