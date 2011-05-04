from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from mailer.models import Message

class AccountTest(TestCase):
    fixtures = ['auth.json', 'foirequest.json']

    def test_account_page(self):
        ok = self.client.login(username='sw', password='wrong')
        self.assertFalse(ok)
        ok = self.client.login(username='sw', password='froide')
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        self.client.logout()
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 403)
        self.client.get(reverse('account-login'))
        response = self.client.post(reverse('account-login'),
                {"email": "doesnt@exist.com",
                "password": "foobar"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse('account-login'),
                {"email": "mail@stefanwehrmeyer.com",
                "password": "dummy"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse('account-login'),
                {"email": "mail@stefanwehrmeyer.com",
                "password": "froide"})
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('account-logout'))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('account-login') + "?simple")
        self.assertIn("simple_base.html", map(lambda x: x.name, response.templates))
        response = self.client.post(reverse('account-login') + "?simple",
                {"email": "mail@stefanwehrmeyer.com",
                "password": "froide"})
        self.assertTrue(response.status_code, 302)
        self.assertIn("simple", response['location'])

    def test_signup(self):
        self.client.logout()
        post = {"first_name": "Horst",
                "last_name": "Porst",
                "user_email": "horst.porst@example.com"}
        response = self.client.post(reverse('account-signup'), post)
        self.assertTrue(response.status_code, 302)
        user = User.objects.get(email=post['user_email'])
        self.assertEqual(user.first_name, post['first_name'])
        self.assertEqual(user.last_name, post['last_name'])
        messages = Message.objects.filter(to_address=post['user_email'])
        self.assertEqual(len(messages), 1)
