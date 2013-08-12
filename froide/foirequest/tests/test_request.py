from __future__ import with_statement

import re
from datetime import datetime, timedelta
import os

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.conf import settings
from django.core import mail
from django.utils import timezone

from froide.publicbody.models import PublicBody, FoiLaw
from froide.foirequest.tests import factories
from froide.foirequest.models import FoiRequest, FoiMessage, FoiAttachment
from froide.helper.test_utils import skip_if_environ


class RequestTest(TestCase):

    def setUp(self):
        factories.make_world()

    def test_public_body_logged_in_request(self):
        ok = self.client.login(username='sw', password='froide')
        self.assertTrue(ok)

        user = User.objects.get(username='sw')
        profile = user.get_profile()
        profile.organization = 'ACME Org'
        profile.save()

        pb = PublicBody.objects.all()[0]
        old_number = pb.number_of_requests
        post = {"subject": "Test-Subject", "body": "This is a test body",
                "law": str(pb.default_law.pk)}
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.filter(user=user, public_body=pb).order_by("-id")[0]
        self.assertIsNotNone(req)
        self.assertFalse(req.public)
        self.assertEqual(req.status, "awaiting_response")
        self.assertEqual(req.visibility, 1)
        self.assertEqual(old_number + 1, req.public_body.number_of_requests)
        self.assertEqual(req.title, post['subject'])
        message = req.foimessage_set.all()[0]
        self.assertIn(post['body'], message.plaintext)
        self.assertIn('\n%s\n' % user.get_full_name(), message.plaintext)
        self.assertIn('\n%s\n' % profile.organization, message.plaintext)
        self.client.logout()
        response = self.client.post(reverse('foirequest-make_public',
                kwargs={"slug": req.slug}), {})
        self.assertEqual(response.status_code, 403)
        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('foirequest-make_public',
                kwargs={"slug": req.slug}), {})
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.published.get(id=req.id)
        self.assertTrue(req.public)

    def test_public_body_new_user_request(self):
        self.client.logout()
        factories.UserFactory.create(email="dummy@example.com")
        pb = PublicBody.objects.all()[0]
        post = {"subject": "Test-Subject With New User",
                "body": "This is a test body with new user",
                "first_name": "Stefan", "last_name": "Wehrmeyer",
                "user_email": "dummy@example.com",
                "law": pb.laws.all()[0].pk}
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}), post)
        self.assertTrue(response.context['user_form']['user_email'].errors)
        self.assertEqual(response.status_code, 400)
        post = {"subject": "Test-Subject With New User",
                "body": "This is a test body with new user",
                "first_name": "Stefan", "last_name": "Wehrmeyer",
                "address": "TestStreet 3\n55555 Town",
                "user_email": "sw@example.com",
                "terms": "on",
                "law": str(FoiLaw.get_default_law(pb).id)}
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
        mes = req.messages[0]
        mes.timestamp = mes.timestamp - timedelta(days=2)
        mes.save()
        self.assertEqual(req.status, "awaiting_response")
        self.assertEqual(req.visibility, 1)
        self.assertEqual(len(mail.outbox), 3)
        message = mail.outbox[1]
        self.assertIn('Legal Note: This mail was sent through a Freedom Of Information Portal.', message.body)
        self.assertIn(req.secret_address, message.extra_headers.get('Reply-To', ''))
        if settings.FROIDE_CONFIG['dryrun']:
            self.assertEqual(message.to[0], "%s@%s" % (req.public_body.email.replace("@", "+"), settings.FROIDE_CONFIG['dryrun_domain']))
        else:
            self.assertEqual(message.to[0], req.public_body.email)
        self.assertEqual(message.subject, req.title)
        resp = self.client.post(reverse('foirequest-set_status',
            kwargs={"slug": req.slug}))
        self.assertEqual(resp.status_code, 400)
        response = self.client.post(reverse('foirequest-set_law',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 400)
        new_foi_email = "foi@" + pb.email.split("@")[1]
        req.add_message_from_email({
            'msgobj': None,
            'date': timezone.now() - timedelta(days=1),
            'subject': u"Re: %s" % req.title,
            'body': u"""Message""",
            'html': None,
            'from': ("FoI Officer", new_foi_email),
            'to': [(req.user.get_full_name(), req.secret_address)],
            'cc': [],
            'resent_to': [],
            'resent_cc': [],
            'attachments': []
        }, "FAKE_ORIGINAL")
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertTrue(req.awaits_classification())
        self.assertEqual(len(req.messages), 2)
        self.assertEqual(req.messages[1].sender_email, new_foi_email)
        self.assertEqual(req.messages[1].sender_public_body,
                req.public_body)
        response = self.client.get(reverse('foirequest-show',
            kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(req.status_settable)
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": "invalid_status_settings_now"})
        self.assertEqual(response.status_code, 400)
        costs = "123.45"
        status = "awaiting_response"
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": status, "costs": costs})
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.costs, float(costs))
        self.assertEqual(req.status, status)
        # send reply
        old_len = len(mail.outbox)
        response = self.client.post(reverse('foirequest-send_message',
                kwargs={"slug": req.slug}), {})
        self.assertEqual(response.status_code, 400)
        post = {"message": "My custom reply"}
        response = self.client.post(reverse('foirequest-send_message',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 400)
        post["to"] = 'abc'
        response = self.client.post(reverse('foirequest-send_message',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 400)
        post["to"] = '9' * 10
        response = self.client.post(reverse('foirequest-send_message',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 400)
        post["subject"] = "Re: Custom subject"
        post["to"] = str(req.possible_reply_addresses().values()[0].id)
        response = self.client.post(reverse('foirequest-send_message',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 302)
        new_len = len(mail.outbox)
        self.assertEqual(old_len + 2, new_len)
        message = filter(lambda x: post['subject'] == x.subject, mail.outbox)[-1]
        self.assertTrue(message.body.startswith(post['message']))
        self.assertIn('Legal Note: This mail was sent through a Freedom Of Information Portal.', message.body)
        self.assertIn(user.get_profile().address, message.body)
        self.assertIn(new_foi_email, message.to[0])
        req._messages = None
        foimessage = list(req.messages)[-1]
        self.assertEqual(foimessage.recipient_public_body, req.public_body)
        self.assertTrue(req.law.meta)
        other_laws = req.law.combined.all()
        post = {"law": str(other_laws[0].pk)}
        response = self.client.post(reverse('foirequest-set_law',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('foirequest-show',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('foirequest-set_law',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 400)
        # logout
        self.client.logout()

        response = self.client.post(reverse('foirequest-set_law',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 403)

        response = self.client.post(reverse('foirequest-send_message',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": status, "costs": costs})
        self.assertEqual(response.status_code, 403)
        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('foirequest-set_law',
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(reverse('foirequest-send_message',
                kwargs={"slug": req.slug}), post)
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
                "law": str(settings.FROIDE_CONFIG['default_law']),
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
                lambda x: req.secret_address in x.extra_headers.get('Reply-To', ''),
                mail.outbox))
        self.assertEqual(message_count, 1)
        # resent
        response = self.client.post(reverse('publicbody-confirm'),
                {"public_body": pb.pk})
        self.assertEqual(response.status_code, 302)
        message_count = len(filter(
                lambda x: req.secret_address in x.extra_headers.get('Reply-To', ''),
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
        post['public_body'] = '9' * 10  # not that many in fixture
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
                lambda x: req.secret_address in x.extra_headers.get('Reply-To', ''),
                mail.outbox)
        self.assertEqual(len(messages), 1)
        message = messages[0]
        if settings.FROIDE_CONFIG['dryrun']:
            self.assertEqual(message.to[0], "%s@%s" % (
                pb.email.replace("@", "+"), settings.FROIDE_CONFIG['dryrun_domain']))
        else:
            self.assertEqual(message.to[0], pb.email)
        self.assertEqual(message.subject, req.title)

    def test_foi_email_settings(self):
        pb = PublicBody.objects.all()[0]
        self.client.login(username="dummy", password="froide")
        post = {"subject": "Another Third Test-Subject",
                "body": "This is another test body",
                "public_body": str(pb.pk),
                'law': str(pb.default_law.pk),
                "public": "on"}
        email_func = lambda u, s: 'email+%s@foi.example.com' % u
        with self.settings(
            FOI_EMAIL_FIXED_FROM_ADDRESS=False,
            FOI_EMAIL_FUNC=email_func
        ):
            response = self.client.post(
                    reverse('foirequest-submit_request'), post)
            self.assertEqual(response.status_code, 302)
            req = FoiRequest.objects.get(title=post['subject'])
            self.assertTrue(req.messages[0].sent)
            addr = email_func(req.user.username, '')
            self.assertEqual(req.secret_address, addr)

    def test_logged_in_request_no_public_body(self):
        self.client.login(username="dummy", password="froide")
        post = {"subject": "An Empty Public Body Request",
                "body": "This is another test body",
                "law": str(FoiLaw.get_default_law().id),
                "public_body": '',
                "public": "on"}
        response = self.client.post(
                reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post['subject'])
        response = self.client.get(req.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        message = req.foimessage_set.all()[0]
        law = FoiLaw.get_default_law()
        self.assertIn(law.get_letter_start_text({}), message.plaintext)
        self.assertIn(law.get_letter_end_text({}), message.plaintext)

        # suggest public body
        other_req = FoiRequest.objects.filter(public_body__isnull=False)[0]
        for pb in PublicBody.objects.all():
            if law not in pb.laws.all():
                break
        assert FoiLaw.get_default_law(pb) != law
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
        self.assertEqual([t.public_body for t in req.publicbodysuggestion_set.all()], [pb])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], req.user.email)
        response = self.client.post(
                reverse('foirequest-suggest_public_body',
                kwargs={"slug": req.slug}),
                {"public_body": str(pb.pk),
                "reason": "A good reason"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual([t.public_body for t in req.publicbodysuggestion_set.all()], [pb])
        self.assertEqual(len(mail.outbox), 1)

        # set public body
        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug + "garbage"}),
                {"suggestion": str(pb.pk)})
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
                {"suggestion": "9" * 10})
        self.assertEqual(response.status_code, 400)
        self.client.logout()
        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug}),
                {"suggestion": str(pb.pk)})
        self.assertEqual(response.status_code, 403)
        self.client.login(username="dummy", password="froide")
        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug}),
                {"suggestion": str(pb.pk)})
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post['subject'])
        message = req.foimessage_set.all()[0]
        self.assertIn(req.law.get_letter_start_text({}), message.plaintext)
        self.assertIn(req.law.get_letter_end_text({}), message.plaintext)
        self.assertNotEqual(req.law, law)
        self.assertEqual(req.public_body, pb)
        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug}),
                {"suggestion": str(pb.pk)})
        self.assertEqual(response.status_code, 400)

    def test_postal_reply(self):
        self.client.login(username='sw', password='froide')
        pb = PublicBody.objects.all()[0]
        post = {"subject": "Totally Random Request",
                "body": "This is another test body",
                "public_body": str(pb.pk),
                "law": str(pb.default_law.pk),
                "public": "on"}
        response = self.client.post(
                reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post['subject'])
        response = self.client.get(reverse("foirequest-show",
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
        # Date message back
        message = req.foimessage_set.all()[0]
        message.timestamp = timezone.utc.localize(
            datetime(2011, 1, 1, 0, 0, 0))
        message.save()

        path = os.path.join(settings.PROJECT_ROOT, "testdata", "test.pdf")
        file_size = os.path.getsize(path)
        f = file(path, "rb")
        post = {"date": "3000-01-01",  # far future
                "sender": "Some Sender",
                "subject": "",
                "text": "Some Text",
                "scan": ""}

        self.client.logout()
        response = self.client.post(reverse("foirequest-add_postal_reply",
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 403)
        self.client.login(username="sw", password="froide")

        pb = req.public_body
        req.public_body = None
        req.save()
        response = self.client.post(reverse("foirequest-add_postal_reply",
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 400)
        req.public_body = pb
        req.save()

        response = self.client.post(reverse("foirequest-add_postal_reply",
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 400)
        post['date'] = "01/41garbl"
        response = self.client.post(reverse("foirequest-add_postal_reply",
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 400)
        post['date'] = "2011-01-02"
        post['scan'] = f
        response = self.client.post(reverse("foirequest-add_postal_reply",
                kwargs={"slug": req.slug}), post)
        self.assertEqual(response.status_code, 302)
        f.close()
        message = req.foimessage_set.all()[1]
        attachment = message.foiattachment_set.all()[0]
        self.assertEqual(attachment.file.size, file_size)
        self.assertEqual(attachment.size, file_size)
        self.assertEqual(attachment.name, 'test.pdf')

        # Change name in order to upload it again
        attachment.name = 'other_test.pdf'
        attachment.save()

        f = file(path, "rb")
        response = self.client.post(reverse('foirequest-add_postal_reply_attachment',
            kwargs={"slug": req.slug, "message_id": "9" * 5}),
            {"scan": f})
        f.close()
        self.assertEqual(response.status_code, 404)

        f = file(path, "rb")
        self.client.logout()
        response = self.client.post(reverse('foirequest-add_postal_reply_attachment',
            kwargs={"slug": req.slug, "message_id": message.pk}),
            {"scan": f})
        f.close()
        self.assertEqual(response.status_code, 403)

        f = file(path, "rb")
        self.client.login(username="dummy", password="froide")
        response = self.client.post(reverse('foirequest-add_postal_reply_attachment',
            kwargs={"slug": req.slug, "message_id": message.pk}),
            {"scan": f})
        f.close()
        self.assertEqual(response.status_code, 403)

        f = file(path, "rb")
        self.client.logout()
        self.client.login(username='sw', password='froide')
        message = req.foimessage_set.all()[0]
        response = self.client.post(reverse('foirequest-add_postal_reply_attachment',
            kwargs={"slug": req.slug, "message_id": message.pk}),
            {"scan": f})
        f.close()
        self.assertEqual(response.status_code, 400)

        message = req.foimessage_set.all()[1]
        response = self.client.post(reverse('foirequest-add_postal_reply_attachment',
            kwargs={"slug": req.slug, "message_id": message.pk}))
        self.assertEqual(response.status_code, 400)

        f = file(path, "rb")
        response = self.client.post(reverse('foirequest-add_postal_reply_attachment',
            kwargs={"slug": req.slug, "message_id": message.pk}),
            {"scan": f})
        f.close()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(message.foiattachment_set.all()), 2)

        # Adding the same document again should override the first one
        f = file(path, "rb")
        response = self.client.post(reverse('foirequest-add_postal_reply_attachment',
            kwargs={"slug": req.slug, "message_id": message.pk}),
            {"scan": f})
        f.close()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(message.foiattachment_set.all()), 2)

    # def test_public_body_logged_in_public_request(self):
    #     ok = self.client.login(username='sw', password='froide')
    #     user = User.objects.get(username='sw')
    #     pb = PublicBody.objects.all()[0]
    #     post = {"subject": "Test-Subject", "body": "This is a test body",
    #             "public": "on",
    #             "law": pb.default_law.pk}
    #     response = self.client.post(reverse('foirequest-submit_request',
    #             kwargs={"public_body": pb.slug}), post)
    #     self.assertEqual(response.status_code, 302)

    def test_set_message_sender(self):
        from froide.foirequest.forms import MessagePublicBodySenderForm
        mail.outbox = []
        self.client.login(username="dummy", password="froide")
        pb = PublicBody.objects.all()[0]
        post = {"subject": "A simple test request",
                "body": "This is another test body",
                "law": str(FoiLaw.get_default_law().id),
                "public_body": str(pb.id),
                "public": "on"}
        response = self.client.post(
                reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)
        req = FoiRequest.objects.get(title=post['subject'])
        req.add_message_from_email({
            'msgobj': None,
            'date': timezone.now() + timedelta(days=1),
            'subject': u"Re: %s" % req.title,
            'body': u"""Message""",
            'html': None,
            'from': ("FoI Officer", "randomfoi@example.com"),
            'to': [(req.user.get_full_name(), req.secret_address)],
            'cc': [],
            'resent_to': [],
            'resent_cc': [],
            'attachments': []
        }, "FAKE_ORIGINAL")
        req = FoiRequest.objects.get(title=post['subject'])
        self.assertEqual(len(req.messages), 2)
        self.assertEqual(len(mail.outbox), 3)
        notification = mail.outbox[-1]
        match = re.search('https?://[^/]+(/.*?/%d/[^\s]+)' % req.user.pk,
                notification.body)
        self.assertIsNotNone(match)
        url = match.group(1)
        self.client.logout()
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        message = req.messages[1]
        self.assertIn(req.get_absolute_short_url(), response['Location'])
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 200)
        form = MessagePublicBodySenderForm(message)
        post_var = form.add_prefix("sender")
        self.assertTrue(message.is_response)
        alternate_pb = PublicBody.objects.all()[1]
        response = self.client.post(
                reverse('foirequest-set_message_sender',
                kwargs={"slug": req.slug, "message_id": "9" * 8}),
                {post_var: alternate_pb.id})
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(message.sender_public_body, alternate_pb)

        self.client.logout()
        response = self.client.post(
                reverse('foirequest-set_message_sender',
                kwargs={"slug": req.slug, "message_id": str(message.pk)}),
                {post_var: alternate_pb.id})
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(message.sender_public_body, alternate_pb)

        self.client.login(username="sw", password="froide")
        response = self.client.post(
                reverse('foirequest-set_message_sender',
                kwargs={"slug": req.slug, "message_id": str(message.pk)}),
                {post_var: alternate_pb.id})
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(message.sender_public_body, alternate_pb)

        self.client.logout()
        self.client.login(username="dummy", password="froide")
        mes = req.messages[0]
        response = self.client.post(
                reverse('foirequest-set_message_sender',
                kwargs={"slug": req.slug, "message_id": str(mes.pk)}),
                {post_var: str(alternate_pb.id)})
        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(message.sender_public_body, alternate_pb)

        response = self.client.post(
                reverse('foirequest-set_message_sender',
                kwargs={"slug": req.slug,
                    "message_id": message.pk}),
                {post_var: "9" * 5})
        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(message.sender_public_body, alternate_pb)

        response = self.client.post(
                reverse('foirequest-set_message_sender',
                kwargs={"slug": req.slug,
                    "message_id": message.pk}),
                {post_var: str(alternate_pb.id)})
        self.assertEqual(response.status_code, 302)
        message = FoiMessage.objects.get(pk=message.pk)
        self.assertEqual(message.sender_public_body, alternate_pb)

    def test_mark_not_foi(self):
        req = FoiRequest.objects.all()[0]
        self.assertTrue(req.is_foi)
        response = self.client.post(reverse('foirequest-mark_not_foi',
                kwargs={"slug": req.slug + "-blub"}))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse('foirequest-mark_not_foi',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)

        self.client.login(username="dummy", password="froide")
        response = self.client.post(reverse('foirequest-mark_not_foi',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)

        req = FoiRequest.objects.get(pk=req.pk)
        self.assertTrue(req.is_foi)
        self.client.logout()
        self.client.login(username="sw", password="froide")
        response = self.client.post(reverse('foirequest-mark_not_foi',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertFalse(req.is_foi)

    def test_mark_checked(self):
        req = FoiRequest.objects.all()[0]
        req.checked = False
        req.save()
        self.assertFalse(req.checked)
        response = self.client.post(reverse('foirequest-mark_checked',
                kwargs={"slug": req.slug + "-blub"}))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse('foirequest-mark_checked',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)

        self.client.login(username="dummy", password="froide")
        response = self.client.post(reverse('foirequest-mark_checked',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)

        req = FoiRequest.objects.get(pk=req.pk)
        self.assertFalse(req.checked)
        self.client.logout()
        self.client.login(username="sw", password="froide")
        response = self.client.post(reverse('foirequest-mark_checked',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertTrue(req.checked)

    def test_escalation_message(self):
        req = FoiRequest.objects.all()[0]
        response = self.client.post(reverse('foirequest-escalation_message',
                kwargs={"slug": req.slug + 'blub'}))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse('foirequest-escalation_message',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)
        ok = self.client.login(username="dummy", password="froide")
        self.assertTrue(ok)
        response = self.client.post(reverse('foirequest-escalation_message',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)
        self.client.logout()
        self.client.login(username="sw", password="froide")
        response = self.client.post(reverse('foirequest-escalation_message',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 400)
        mail.outbox = []
        response = self.client.post(reverse('foirequest-escalation_message',
                kwargs={"slug": req.slug}), {
                    'subject': 'My Escalation Subject',
                    'message': 'My Escalation Message'
                }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(req.get_absolute_url(), response['Location'])
        self.assertEqual(req.law.mediator, req.messages[-1].recipient_public_body)
        self.assertEqual(len(mail.outbox), 2)

    def test_set_tags(self):
        req = FoiRequest.objects.all()[0]

        # Bad method
        response = self.client.get(reverse('foirequest-set_tags',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 405)

        # Bad slug
        response = self.client.post(reverse('foirequest-set_tags',
                kwargs={"slug": req.slug + 'blub'}))
        self.assertEqual(response.status_code, 404)

        # Not logged in
        self.client.logout()
        response = self.client.post(reverse('foirequest-set_tags',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)

        # Not staff
        self.client.login(username='dummy', password='froide')
        response = self.client.post(reverse('foirequest-set_tags',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)

        # Bad form
        self.client.logout()
        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('foirequest-set_tags',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(req.tags.all()), 0)

        response = self.client.post(reverse('foirequest-set_tags',
                kwargs={"slug": req.slug}),
                {'tags': 'SomeTag, "Another Tag", SomeTag'})
        self.assertEqual(response.status_code, 302)
        tags = req.tags.all()
        self.assertEqual(len(tags), 2)
        self.assertIn('SomeTag', [t.name for t in tags])
        self.assertIn('Another Tag', [t.name for t in tags])

    def test_set_summary(self):
        req = FoiRequest.objects.all()[0]

        # Bad method
        response = self.client.get(reverse('foirequest-set_summary',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 405)

        # Bad slug
        response = self.client.post(reverse('foirequest-set_summary',
                kwargs={"slug": req.slug + 'blub'}))
        self.assertEqual(response.status_code, 404)

        # Not logged in
        self.client.logout()
        response = self.client.post(reverse('foirequest-set_summary',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)

        # Not user of request
        self.client.login(username='dummy', password='froide')
        response = self.client.post(reverse('foirequest-set_summary',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)

        # Request not final
        self.client.logout()
        self.client.login(username='sw', password='froide')
        req.status = 'awaiting_response'
        req.save()
        response = self.client.post(reverse('foirequest-set_summary',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 400)

        # No resolution given
        req.status = 'resolved'
        req.save()
        response = self.client.post(reverse('foirequest-set_summary',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 400)

        res = "This is resolved"
        response = self.client.post(reverse('foirequest-set_summary',
                kwargs={"slug": req.slug}), {"summary": res})
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(id=req.id)
        self.assertEqual(req.summary, res)

    def test_approve_attachment(self):
        req = FoiRequest.objects.all()[0]
        mes = req.messages[-1]
        att = factories.FoiAttachmentFactory.create(belongs_to=mes, approved=False)

        # Bad method
        response = self.client.get(reverse('foirequest-approve_attachment',
                kwargs={"slug": req.slug, "attachment": att.id}))
        self.assertEqual(response.status_code, 405)

        # Bad slug
        response = self.client.post(reverse('foirequest-approve_attachment',
                kwargs={"slug": req.slug + 'blub', "attachment": att.id}))
        self.assertEqual(response.status_code, 404)

        # Not logged in
        self.client.logout()
        response = self.client.post(reverse('foirequest-approve_attachment',
                kwargs={"slug": req.slug, "attachment": att.id}))
        self.assertEqual(response.status_code, 403)

        # Not user of request
        self.client.login(username='dummy', password='froide')
        response = self.client.post(reverse('foirequest-approve_attachment',
                kwargs={"slug": req.slug, "attachment": att.id}))
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('foirequest-approve_attachment',
                kwargs={"slug": req.slug, "attachment": '9' * 8}))
        self.assertEqual(response.status_code, 404)

        user = User.objects.get(username='sw')
        user.is_staff = False
        user.save()

        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('foirequest-approve_attachment',
                kwargs={"slug": req.slug, "attachment": att.id}))
        self.assertEqual(response.status_code, 302)
        att = FoiAttachment.objects.get(id=att.id)
        self.assertTrue(att.approved)

        att.approved = False
        att.can_approve = False
        att.save()
        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('foirequest-approve_attachment',
                kwargs={"slug": req.slug, "attachment": att.id}))
        self.assertEqual(response.status_code, 403)
        att = FoiAttachment.objects.get(id=att.id)
        self.assertFalse(att.approved)
        self.assertFalse(att.can_approve)

        self.client.logout()
        self.client.login(username='dummy_staff', password='froide')
        response = self.client.post(reverse('foirequest-approve_attachment',
                kwargs={"slug": req.slug, "attachment": att.id}))
        self.assertEqual(response.status_code, 302)
        att = FoiAttachment.objects.get(id=att.id)
        self.assertTrue(att.approved)
        self.assertFalse(att.can_approve)

    def test_make_same_request(self):
        fake_mes = factories.FoiMessageFactory.create(not_publishable=True)
        req = FoiRequest.objects.all()[0]
        mes = req.messages[-1]

        # req doesn't exist
        response = self.client.post(reverse('foirequest-make_same_request',
                kwargs={"slug": req.slug + 'blub', "message_id": '9' * 4}))
        self.assertEqual(response.status_code, 404)

        # message doesn't exist
        response = self.client.post(reverse('foirequest-make_same_request',
                kwargs={"slug": req.slug, "message_id": '9' * 4}))
        self.assertEqual(response.status_code, 404)

        # message is publishable
        response = self.client.post(reverse('foirequest-make_same_request',
                kwargs={"slug": req.slug, "message_id": mes.id}))
        self.assertEqual(response.status_code, 400)

        # message does not belong to request
        response = self.client.post(reverse('foirequest-make_same_request',
                kwargs={"slug": req.slug, "message_id": fake_mes.id}))
        self.assertEqual(response.status_code, 400)

        # not loged in, no form
        mes.not_publishable = True
        mes.save()

        response = self.client.get(reverse('foirequest-show', kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('foirequest-make_same_request',
                kwargs={"slug": req.slug, "message_id": mes.id}))
        self.assertEqual(response.status_code, 400)

        # user made original request
        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('foirequest-make_same_request',
                kwargs={"slug": req.slug, "message_id": mes.id}))
        self.assertEqual(response.status_code, 400)

        # make request
        mail.outbox = []
        self.client.logout()
        self.client.login(username='dummy', password='froide')
        response = self.client.post(reverse('foirequest-make_same_request',
                kwargs={"slug": req.slug, "message_id": mes.id}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)
        user = User.objects.get(username='dummy')
        same_req = FoiRequest.objects.get(same_as=req, user=user)
        self.assertIn(same_req.get_absolute_url(), response['Location'])

        response = self.client.post(reverse('foirequest-make_same_request',
                kwargs={"slug": req.slug, "message_id": mes.id}))
        self.assertEqual(response.status_code, 400)
        same_req = FoiRequest.objects.get(same_as=req, user=user)

        same_mes = factories.FoiMessageFactory.create(
            request=same_req, not_publishable=True)
        self.client.logout()
        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('foirequest-make_same_request',
                kwargs={"slug": same_req.slug, "message_id": same_mes.id}))
        self.assertEqual(response.status_code, 400)

        self.client.logout()
        mail.outbox = []
        post = {"first_name": "Bob",
                "last_name": "Bobbington",
                "address": "MyAddres 12\nB-Town",
                "user_email": "bob@example.com",
                "terms": "on"
        }
        response = self.client.post(reverse('foirequest-make_same_request',
                kwargs={"slug": same_req.slug, "message_id": same_mes.id}), post)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FoiRequest.objects.filter(same_as=req).count(), 2)
        same_req2 = FoiRequest.objects.get(same_as=req, user__email=post['user_email'])
        self.assertEqual(same_req2.status, "awaiting_user_confirmation")
        self.assertEqual(same_req2.visibility, 0)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to[0], post['user_email'])
        match = re.search('/(\d+)/%d/(\w+)/' % (same_req2.pk), message.body)
        self.assertIsNotNone(match)
        new_user = User.objects.get(id=int(match.group(1)))
        self.assertFalse(new_user.is_active)
        secret = match.group(2)
        response = self.client.get(reverse('account-confirm',
                kwargs={'user_id': new_user.pk,
                'secret': secret, 'request_id': same_req2.pk}))
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(id=new_user.pk)
        self.assertTrue(new_user.is_active)
        same_req2 = FoiRequest.objects.get(pk=same_req2.pk)
        self.assertEqual(same_req2.status, "awaiting_response")
        self.assertEqual(same_req2.visibility, 2)
        self.assertEqual(len(mail.outbox), 3)

    def test_empty_costs(self):
        req = FoiRequest.objects.all()[0]
        user = User.objects.get(username='sw')
        req.status = 'awaits_classification'
        req.user = user
        req.save()
        factories.FoiMessageFactory.create(
            status=None,
            request=req
        )
        self.client.login(username='sw', password='froide')
        status = 'awaiting_response'
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": status, "costs": "", 'resolution': ''})
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.costs, 0.0)
        self.assertEqual(req.status, status)

    def test_resolution(self):
        req = FoiRequest.objects.all()[0]
        user = User.objects.get(username='sw')
        req.status = 'awaits_classification'
        req.user = user
        req.save()
        factories.FoiMessageFactory.create(
            status=None,
            request=req
        )
        self.client.login(username='sw', password='froide')
        status = 'resolved'
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": status, "costs": "", 'resolution': ''})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": status, "costs": "", 'resolution': 'bogus'})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": status, "costs": "", 'resolution': 'successful'})
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.costs, 0.0)
        self.assertEqual(req.status, 'resolved')
        self.assertEqual(req.resolution, 'successful')

    def test_redirect(self):
        req = FoiRequest.objects.all()[0]
        user = User.objects.get(username='sw')
        req.status = 'awaits_classification'
        req.user = user
        req.save()
        factories.FoiMessageFactory.create(
            status=None,
            request=req
        )
        pb = PublicBody.objects.all()[1]
        # old_due = req.due_date
        self.assertNotEqual(req.public_body, pb)
        self.client.login(username='sw', password='froide')
        status = 'request_redirected'
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": status, "costs": "", 'resolution': ''})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse('foirequest-set_status',
                kwargs={"slug": req.slug}),
                {"status": status, "costs": "", 'redirected': '9' * 7})
        self.assertEqual(response.status_code, 400)
        # response = self.client.post(reverse('foirequest-set_status',
        #         kwargs={"slug": req.slug}),
        #         {"status": status, "costs": "", 'redirected': str(pb.pk)})
        # self.assertEqual(response.status_code, 302)
        # req = FoiRequest.objects.get(pk=req.pk)
        # self.assertEqual(req.costs, 0.0)
        # self.assertEqual(req.status, 'awaiting_response')
        # self.assertEqual(req.resolution, '')
        # self.assertEqual(req.public_body, pb)
        # self.assertNotEqual(old_due, req.due_date)

    @skip_if_environ('FROIDE_SKIP_SEARCH')
    def test_search(self):
        pb = PublicBody.objects.all()[0]
        response = self.client.get('%s?q=%s' % (
            reverse('foirequest-search'), pb.name[:6]))
        self.assertIn(pb.name, response.content)
        self.assertEqual(response.status_code, 200)


class MediatorTest(TestCase):

    def setUp(self):
        self.site = factories.make_world()

    def test_hiding_content(self):
        req = FoiRequest.objects.all()[0]
        mediator = req.law.mediator
        req.add_escalation_message('Escalate', 'Content')
        req = FoiRequest.objects.all()[0]
        req.add_message_from_email({
            'msgobj': None,
            'date': timezone.now(),
            'subject': 'Reply',
            'body': 'Content',
            'html': 'html',
            'from': ('Name', mediator.email),
            'to': [req.secret_address],
            'cc': [],
            'resent_to': [],
            'resent_cc': [],
            'attachments': []
        }, '')
        req = FoiRequest.objects.all()[0]
        last = req.messages[-1]
        self.assertTrue(last.content_hidden)

    def test_no_public_body(self):
        user = User.objects.get(username='sw')
        req = factories.FoiRequestFactory.create(
            user=user,
            public_body=None,
            status='public_body_needed',
            site=self.site
        )
        req.save()
        self.client.login(username='sw', password='froide')
        response = self.client.get(req.get_absolute_url())
        self.assertNotIn('Mediation', response.content)
        response = self.client.post(reverse('foirequest-escalation_message',
            kwargs={'slug': req.slug}))
        self.assertEqual(response.status_code, 400)
        message = list(response.context['messages'])[0]
        self.assertIn('cannot be escalated', message.message)


class JurisdictionTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()
        self.pb = PublicBody.objects.filter(jurisdiction__slug='nrw')[0]

    def test_letter_public_body(self):
        self.client.login(username='sw', password='froide')
        post = {
            "subject": "Jurisdiction-Test-Subject",
            "body": "This is a test body",
            "law": str(self.pb.default_law.pk)
        }
        response = self.client.post(
            reverse('foirequest-submit_request',
                kwargs={"public_body": self.pb.slug}
        ), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title='Jurisdiction-Test-Subject')
        law = FoiLaw.objects.get(meta=True, jurisdiction__slug='nrw')
        self.assertEqual(req.law, law)
        mes = req.messages[0]
        self.assertIn(law.letter_end, mes.plaintext)

    def test_letter_set_public_body(self):
        self.client.login(username='sw', password='froide')
        post = {
            "subject": "Jurisdiction-Test-Subject",
            "body": "This is a test body",
            'law': str(FoiLaw.get_default_law().pk),
            'publicbody': ''
        }
        response = self.client.post(
            reverse('foirequest-submit_request'), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(
            title=post['subject']
        )
        default_law = FoiLaw.get_default_law()
        self.assertEqual(req.law, default_law)
        mes = req.messages[0]
        self.assertIn(default_law.letter_end, mes.plaintext)
        self.assertIn(default_law.letter_end, mes.plaintext_redacted)

        response = self.client.post(
                reverse('foirequest-suggest_public_body',
                kwargs={"slug": req.slug}),
                {"public_body": str(self.pb.pk),
                "reason": "A good reason"})
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
                reverse('foirequest-set_public_body',
                kwargs={"slug": req.slug}),
                {"suggestion": str(self.pb.pk)})
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post['subject'])
        law = FoiLaw.objects.get(meta=True, jurisdiction__slug='nrw')
        self.assertEqual(req.law, law)
        mes = req.messages[0]
        self.assertNotEqual(default_law.letter_end, law.letter_end)
        self.assertIn(law.letter_end, mes.plaintext)
        self.assertIn(law.letter_end, mes.plaintext_redacted)
