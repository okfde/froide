from __future__ import with_statement

import re

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from mailer.models import Message

from publicbody.models import PublicBody
from foirequest.models import FoiRequest


class RequestTest(TestCase):
    fixtures = ['auth.json', 'publicbodies.json', 'foirequest.json']

    def test_public_body_logged_in_request(self):
        ok = self.client.login(username='sw', password='froide')
        user = User.objects.get(username='sw')
        self.assertTrue(ok)

        pb = PublicBody.objects.all()[0]
        post = {"subject": "Test-Subject", "body": "This is a test body"}
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.filter(user=user, public_body=pb).get()
        self.assertIsNotNone(req)
        self.assertEqual(req.title, post['subject'])
        message = req.foimessage_set.all()[0]
        self.assertIn(post['body'], message.plaintext)

    def test_public_body_new_user_request(self):
        self.client.logout()
        pb = PublicBody.objects.all()[0]
        post = {"subject": "Test-Subject With New User",
                "body": "This is a test body with new user",
                "first_name": "Stefan", "last_name": "Wehrmeyer",
                "email": "sw@example.com"}
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}), post)
        self.assertEqual(response.status_code, 302)
        user = User.objects.filter(email=post['email']).get()
        self.assertFalse(user.is_active)
        req = FoiRequest.objects.filter(user=user, public_body=pb).get()
        self.assertIsNotNone(req)
        self.assertEqual(req.title, post['subject'])
        message = req.foimessage_set.all()[0]
        self.assertIn(post['body'], message.plaintext)
        message = Message.objects.filter(to_address=post['email']).get()
        match = re.search('/%d/%d/(\w+)/' % (user.pk, req.pk),
                message.message_body)
        self.assertIsNotNone(match)
        secret = match.group(1)
        response = self.client.get(reverse('account-confirm',
                kwargs={'user_id': user.pk,
                'secret': secret, 'request_id': req.pk}))
        message = Message.objects.filter(from_address=req.secret_address).get()

    def test_public_body_not_logged_in_request(self):
        self.client.logout()
        pb = PublicBody.objects.all()[0]
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}),
                {"subject": "Test-Subject", "body": "This is a test body",
                    "email": "test@example.com"})
        self.assertEqual(response.status_code, 400)
        self.assertFormError(response, 'user_form', 'first_name',
                [u'This field is required.'])
        self.assertFormError(response, 'user_form', 'last_name',
                [u'This field is required.'])
