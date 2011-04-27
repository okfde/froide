from __future__ import with_statement

import re
from datetime import datetime

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
        old_number = pb.number_of_requests
        post = {"subject": "Test-Subject", "body": "This is a test body",
                "law": pb.laws.all()[0].pk}
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.filter(user=user, public_body=pb).get()
        self.assertIsNotNone(req)
        self.assertEqual(req.status, "awaiting_response")
        self.assertEqual(req.visibility, 1)
        self.assertEqual(old_number + 1, req.public_body.number_of_requests)
        self.assertEqual(req.public, False)
        self.assertEqual(req.title, post['subject'])
        message = req.foimessage_set.all()[0]
        self.assertIn(post['body'], message.plaintext)

    def test_public_body_new_user_request(self):
        self.client.logout()
        pb = PublicBody.objects.all()[0]
        post = {"subject": "Test-Subject With New User",
                "body": "This is a test body with new user",
                "first_name": "Stefan", "last_name": "Wehrmeyer",
                "user_email": "sw@example.com",
                "law": pb.laws.all()[0].pk}
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}), post)
        self.assertEqual(response.status_code, 302)
        user = User.objects.filter(email=post['user_email']).get()
        self.assertFalse(user.is_active)
        req = FoiRequest.objects.filter(user=user, public_body=pb).get()
        self.assertIsNotNone(req)
        self.assertEqual(req.title, post['subject'])
        self.assertEqual(req.status, "awaiting_user_confirmation")
        self.assertEqual(req.visibility, 0)
        message = req.foimessage_set.all()[0]
        self.assertIn(post['body'], message.plaintext)
        message = Message.objects.filter(to_address=post['user_email']).get()
        match = re.search('/%d/%d/(\w+)/' % (user.pk, req.pk),
                message.message_body)
        self.assertIsNotNone(match)
        secret = match.group(1)
        response = self.client.get(reverse('account-confirm',
                kwargs={'user_id': user.pk,
                'secret': secret, 'request_id': req.pk}))
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.status, "awaiting_response")
        self.assertEqual(req.visibility, 1)
        message = Message.objects.filter(from_address=req.secret_address).get()
        self.assertEqual(message.to_address, req.public_body.email)
        self.assertEqual(message.subject, req.title)
        resp = self.client.post(reverse('foirequest-set_status',
            kwargs={"slug": req.slug}))
        self.assertEqual(resp.status_code, 400)
        req.add_message_from_email({
            'msgobj': None,
            'date': (datetime.now(),0),
            'subject': u"Re: %s" % req.title,
            'body': u"""Message""",
            'html': None,
            'from': (pb.name, pb.email),
            'to': [(req.user.get_full_name(), req.secret_address)],
            'cc': [],
            'resent_to': [],
            'resent_cc': [],
            'attachments': []
        }, "FAKE_ORIGINAL")
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(len(req.messages), 2)
        self.assertEqual(req.messages[1].sender_email, pb.email)
        response = self.client.get(reverse('foirequest-show',
            kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(req.status_settable)
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": "invalid_status_settings_now"})
        self.assertEqual(response.status_code, 400)
        costs = "123.45"
        status = "requires_payment"
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": status, "costs": costs})
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.costs, float(costs))
        self.assertEqual(req.status, status)

    def test_public_body_not_logged_in_request(self):
        self.client.logout()
        pb = PublicBody.objects.all()[0]
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}),
                {"subject": "Test-Subject", "body": "This is a test body",
                    "user_email": "test@example.com"})
        self.assertEqual(response.status_code, 400)
        self.assertFormError(response, 'user_form', 'first_name',
                [u'This field is required.'])
        self.assertFormError(response, 'user_form', 'last_name',
                [u'This field is required.'])

    def test_logged_in_request_new_public_body_missing(self):
        self.client.login(username="dummy", password="froide")
        response = self.client.post(reverse('foirequest-submit_request'),
                {"subject": "Test-Subject", "body": "This is a test body",
                "public_body": "new"})
        self.assertEqual(response.status_code, 400)
        self.assertFormError(response, 'public_body_form', 'name',
                [u'This field is required.'])
        self.assertFormError(response, 'public_body_form', 'email',
                [u'This field is required.'])
        self.assertFormError(response, 'public_body_form', 'url',
                [u'This field is required.'])

    def test_logged_in_request_new_public_body(self):
        self.client.login(username="dummy", password="froide")
        post = {"subject": "Another Test-Subject",
                "body": "This is a test body",
                "public_body": "new",
                "public": "on",
                "name": "Some New Public Body",
                "email": "public.body@example.com",
                "url": "http://example.com/public/body/"}
        response = self.client.post(
                reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 302)
        pb = PublicBody.objects.filter(name=post['name']).get()
        self.assertEqual(pb.url, post['url'])
        req = FoiRequest.objects.get(public_body=pb)
        self.assertEqual(req.status, "awaiting_publicbody_confirmation")
        self.assertEqual(req.visibility, 2)
        self.assertTrue(req.public)
