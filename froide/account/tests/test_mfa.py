from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
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
