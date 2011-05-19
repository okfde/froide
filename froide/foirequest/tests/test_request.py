from __future__ import with_statement

import re
from datetime import datetime

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.conf import settings
from django.core import mail

from publicbody.models import PublicBody
from foirequest.models import FoiRequest


class RequestTest(TestCase):
    fixtures = ['auth_profile.json', 'publicbody.json', 'foirequest.json']

    def test_public_body_logged_in_request(self):
        ok = self.client.login(username='sw', password='froide')
        user = User.objects.get(username='sw')
        self.assertTrue(ok)

        pb = PublicBody.objects.all()[0]
        old_number = pb.number_of_requests
        post = {"subject": "Test-Subject", "body": "This is a test body",
                "law": pb.default_law.pk}
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
                "user_email": "dummy@example.com", # already exists in fixture
                "law": pb.laws.all()[0].pk}
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}), post)
        self.assertTrue(response.context['user_form']['user_email'].errors)
        self.assertEqual(response.status_code, 400)
        post = {"subject": "Test-Subject With New User",
                "body": "This is a test body with new user",
                "first_name": "Stefan", "last_name": "Wehrmeyer",
                "user_email": "sw@example.com",
                "terms": "on",
                "law": pb.laws.all()[0].pk}
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}), post)
        self.assertEqual(response.status_code, 302)
        user = User.objects.filter(email=post['user_email']).get()
        self.assertFalse(user.is_active)
        req = FoiRequest.objects.filter(user=user, public_body=pb).get()
        self.assertEqual(req.title, post['subject'])
        self.assertEqual(req.description, post['body'])
        self.assertEqual(req.status, "awaiting_user_confirmation")
        self.assertEqual(req.visibility, 0)
        message = req.foimessage_set.all()[0]
        self.assertIn(post['body'], message.plaintext)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(mail.outbox[0].to[0], post['user_email'])
        match = re.search('/%d/%d/(\w+)/' % (user.pk, req.pk),
                message.body)
        self.assertIsNotNone(match)
        secret = match.group(1)
        response = self.client.get(reverse('account-confirm',
                kwargs={'user_id': user.pk,
                'secret': secret, 'request_id': req.pk}))
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.status, "awaiting_response")
        self.assertEqual(req.visibility, 1)
        self.assertEqual(len(mail.outbox), 3)
        message = mail.outbox[1]
        self.assertIn(req.secret_address, message.extra_headers.get('Reply-To',''))
        if settings.FROIDE_DRYRUN:
            self.assertEqual(message.to[0], "%s@%s" % (req.public_body.email.replace("@", "+"), settings.FROIDE_DRYRUN_DOMAIN))
        else:
            self.assertEqual(message.to[0], req.public_body.email)
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
        # send reply
        old_len = len(mail.outbox)
        post = {"message": "My custom reply"}
        response = self.client.post(reverse('foirequest-send_message',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 302)
        new_len = len(mail.outbox)
        self.assertEqual(old_len + 2, new_len)
        message = filter(lambda x: req.title in x.subject, mail.outbox)[-1]
        self.assertEqual(message.body, post['message'])
        # logout
        self.client.logout()
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": status, "costs": costs})
        self.assertEqual(response.status_code, 403)

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
        self.assertFalse(req.messages[0].sent)
        self.client.logout()
        # Confirm public body via admin interface
        response = self.client.post(reverse('publicbody-confirm'),
                {"public_body": pb.pk})
        self.assertEqual(response.status_code, 403)
        # login as not staff
        self.client.login(username='dummy', password='froide')
        response = self.client.post(reverse('publicbody-confirm'),
                {"public_body": pb.pk})
        self.assertEqual(response.status_code, 403)
        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('publicbody-confirm'),
                {"public_body": "argh"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse('publicbody-confirm'))
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse('publicbody-confirm'),
                {"public_body": "9" * 10})
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse('publicbody-confirm'),
                {"public_body": pb.pk})
        self.assertEqual(response.status_code, 302)
        pb = PublicBody.objects.get(id=pb.id)
        req = FoiRequest.objects.get(id=req.id)
        self.assertTrue(pb.confirmed)
        self.assertTrue(req.messages[0].sent)
        message_count = len(filter(
                lambda x: req.secret_address in x.extra_headers.get('Reply-To',''),
                mail.outbox))
        self.assertEqual(message_count, 1)
        # resent
        response = self.client.post(reverse('publicbody-confirm'),
                {"public_body": pb.pk})
        self.assertEqual(response.status_code, 302)
        message_count = len(filter(
                lambda x: req.secret_address in x.extra_headers.get('Reply-To',''),
                mail.outbox))
        self.assertEqual(message_count, 1)

    def test_logged_in_request_with_public_body(self):
        pb = PublicBody.objects.all()[0]
        self.client.login(username="dummy", password="froide")
        post = {"subject": "Another Third Test-Subject",
                "body": "This is another test body",
                "public_body": 'bs',
                "public": "on"}
        response = self.client.post(
                reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 400)
        post['law'] = str(pb.default_law.pk)
        response = self.client.post(
                reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 400)
        post['public_body'] = '9' * 10 # not that many in fixture
        response = self.client.post(
                reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 400)
        post['public_body'] = str(pb.pk)
        post['law'] = '9' * 10
        response = self.client.post(
                reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 400)
        post['law'] = str(pb.default_law.pk)
        response = self.client.post(
                reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post['subject'])
        self.assertEqual(req.public_body.pk, pb.pk)
        self.assertTrue(req.messages[0].sent)
        self.assertEqual(req.law, pb.default_law)

        messages = filter(
                lambda x: req.secret_address in x.extra_headers.get('Reply-To',''),
                mail.outbox)
        self.assertEqual(len(messages), 1)
        message = messages[0]
        if settings.FROIDE_DRYRUN:
            self.assertEqual(message.to[0], "%s@%s" % (
                pb.email.replace("@", "+"), settings.FROIDE_DRYRUN_DOMAIN))
        else:
            self.assertEqual(message.to[0], pb.email)
        self.assertEqual(message.subject, req.title)

    def test_logged_in_request_no_public_body(self):
        self.client.login(username="dummy", password="froide")
        post = {"subject": "An Empty Public Body Request",
                "body": "This is another test body",
                "public_body": '',
                "public": "on"}
        response = self.client.post(
                reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post['subject'])
        response = self.client.get(req.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        # suggest public body
        other_req = FoiRequest.objects.filter(public_body__isnull=False)[0]
        pb = PublicBody.objects.all()[0]
        response = self.client.post(
                reverse('foirequest-suggest_public_body',
                kwargs={"slug": req.slug + "garbage"}),
                {"public_body": str(pb.pk)})
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
                reverse('foirequest-suggest_public_body',
                kwargs={"slug": other_req.slug}),
                {"public_body": str(pb.pk)})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
                reverse('foirequest-suggest_public_body',
                kwargs={"slug": req.slug}),
                {})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
                reverse('foirequest-suggest_public_body',
                kwargs={"slug": req.slug}),
                {"public_body": "9" * 10})
        self.assertEqual(response.status_code, 400)
        self.client.logout()
        self.client.login(username="sw", password="froide")
        mail.outbox = []
        response = self.client.post(
                reverse('foirequest-suggest_public_body',
                kwargs={"slug": req.slug}),
                {"public_body": str(pb.pk),
                "reason": "A good reason"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(req.publicbodysuggestion_set.all()[0].public_body, pb)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], req.user.email)
        # set public body
        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug + "garbage"}),
                {"public_body": str(pb.pk)})
        self.assertEqual(response.status_code, 404)
        self.client.logout()
        self.client.login(username="dummy", password="froide")
        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug}),
                {})
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post['subject'])
        self.assertIsNone(req.public_body)

        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug}),
                {"public_body": "9" * 10})
        self.assertEqual(response.status_code, 400)
        self.client.logout()
        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug}),
                {"public_body": str(pb.pk)})
        self.assertEqual(response.status_code, 403)
        self.client.login(username="dummy", password="froide")
        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug}),
                {"public_body": str(pb.pk)})
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post['subject'])
        self.assertEqual(req.public_body, pb)
        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug}),
                {"public_body": str(pb.pk)})
        self.assertEqual(response.status_code, 400)

