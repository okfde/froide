from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from oauth2_provider.models import get_access_token_model, get_application_model

from froide.foirequest.tests import factories

User = get_user_model()
Application = get_application_model()
AccessToken = get_access_token_model()


class ApiTest(TestCase):
    def setUp(self):
        factories.make_world()
        self.test_user = User.objects.get(username="dummy")
        self.dev_user = User.objects.create_user(
            "dev@example.com", "dev_user", "123456"
        )

        self.application = Application.objects.create(
            name="Test Application",
            redirect_uris="http://localhost http://example.com http://example.org",
            user=self.dev_user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )

        self.access_token = AccessToken.objects.create(
            user=self.test_user,
            scope="read:user",
            expires=timezone.now() + timedelta(seconds=300),
            token="secret-access-token-key",
            application=self.application,
        )
        self.profile_url = reverse("api-user-profile")

    def _create_authorization_header(self, token):
        return "Bearer {0}".format(token)

    def test_authentication_logged_in(self):
        self.client.login(email=self.test_user, password="froide")
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)

    def test_authentication_logged_in_no_jsonp(self):
        self.client.login(email=self.test_user, password="froide")
        response = self.client.get(self.profile_url + "?format=jsonp")
        self.assertNotContains(response, "callback({", status_code=404)

    def test_authentication_not_loggedin(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 401)

    def test_authentication_empty_scope(self):
        self.access_token.scope = ""
        self.access_token.save()

        auth = self._create_authorization_header(self.access_token.token)
        response = self.client.get(self.profile_url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 403)

    def test_authentication_user_scope(self):
        auth = self._create_authorization_header(self.access_token.token)
        response = self.client.get(self.profile_url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"id":%d' % self.test_user.pk)
        self.assertNotContains(response, self.test_user.email)
        self.assertNotContains(response, self.test_user.first_name)

    def test_authentication_profile_scope(self):
        self.access_token.scope = "read:user read:profile"
        self.access_token.save()
        auth = self._create_authorization_header(self.access_token.token)
        response = self.client.get(self.profile_url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"id":%d' % self.test_user.pk)
        self.assertNotContains(response, self.test_user.email)
        self.assertContains(response, self.test_user.first_name)
        self.assertContains(response, self.test_user.last_name)

    def test_authentication_email_scope(self):
        self.access_token.scope = "read:user read:profile read:email"
        self.access_token.save()
        auth = self._create_authorization_header(self.access_token.token)
        response = self.client.get(self.profile_url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"id":%d' % self.test_user.pk)
        self.assertContains(response, self.test_user.email)
        self.assertContains(response, self.test_user.first_name)
        self.assertContains(response, self.test_user.last_name)
