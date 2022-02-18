import os
import re
import zipfile
from datetime import datetime, timedelta
from email.parser import BytesParser as Parser
from io import BytesIO
from unittest import mock
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.http import QueryDict
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from froide.foirequest.foi_mail import (
    add_message_from_email,
    generate_foirequest_files,
    package_foirequest,
)
from froide.foirequest.forms import get_escalation_message_form, get_send_message_form
from froide.foirequest.models import (
    DeliveryStatus,
    FoiAttachment,
    FoiMessage,
    FoiRequest,
)
from froide.foirequest.tests import factories
from froide.foirequest.utils import possible_reply_addresses
from froide.helper.email_parsing import ParsedEmail
from froide.publicbody.models import FoiLaw, PublicBody

User = get_user_model()


class RequestTest(TestCase):
    def setUp(self):
        factories.make_world()
        self.msgobj = Parser().parse(BytesIO())

    def assertForbidden(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account-login"), response["Location"])
        self.assertIn("?next=", response["Location"])

    def test_public_body_logged_in_request(self):
        ok = self.client.login(email="info@fragdenstaat.de", password="froide")
        self.assertTrue(ok)

        user = User.objects.get(username="sw")
        user.organization_name = "ACME Org"
        user.save()

        pb = PublicBody.objects.all()[0]
        old_number = pb.number_of_requests
        post = {
            "subject": "Test-Subject",
            "body": "This is another test body with Ümläut€n",
            "publicbody": pb.pk,
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.filter(user=user, public_body=pb).order_by("-id")[0]
        self.assertIsNotNone(req)
        self.assertFalse(req.public)
        self.assertEqual(req.status, "awaiting_response")
        self.assertEqual(req.visibility, 1)
        self.assertEqual(old_number + 1, req.public_body.number_of_requests)
        self.assertEqual(req.title, post["subject"])
        message = req.foimessage_set.all()[0]
        self.assertIn(post["body"], message.plaintext)
        self.assertIn("\n%s\n" % user.get_full_name(), message.plaintext)
        self.client.logout()
        response = self.client.post(
            reverse("foirequest-make_public", kwargs={"slug": req.slug}), {}
        )
        self.assertForbidden(response)
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse("foirequest-make_public", kwargs={"slug": req.slug}), {}
        )
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.published.get(id=req.id)
        self.assertTrue(req.public)
        self.assertTrue(req.messages[-1].subject.count("[#%s]" % req.pk), 1)
        self.assertTrue(req.messages[-1].subject.endswith("[#%s]" % req.pk))

    def test_public_body_new_user_request(self):
        self.client.logout()
        factories.UserFactory.create(email="dummy@example.com")
        pb = PublicBody.objects.all()[0]
        post = {
            "subject": "Test-Subject With New User",
            "body": "This is a test body with new user",
            "first_name": "Stefan",
            "last_name": "Wehrmeyer",
            "address": "TestStreet 3\n55555 Town",
            "user_email": "sw@example.com",
            "terms": "on",
            "publicbody": pb.pk,
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 302)
        user = User.objects.filter(email=post["user_email"]).get()
        self.assertFalse(user.is_active)
        req = FoiRequest.objects.filter(user=user, public_body=pb).get()
        self.assertEqual(req.title, post["subject"])
        self.assertEqual(req.description, post["body"])
        self.assertEqual(req.status, "awaiting_user_confirmation")
        self.assertEqual(req.visibility, 0)
        message = req.foimessage_set.all()[0]
        self.assertIn(post["body"], message.plaintext)
        self.assertIn(post["body"], message.content)
        self.assertIn(post["body"], message.get_real_content())
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(mail.outbox[0].to[0], post["user_email"])
        match = re.search(r"/%d/%d/(\w+)/" % (user.pk, req.pk), message.body)
        match_full = re.search(r"http://[^/]+(/.+)", message.body)
        self.assertIsNotNone(match)
        self.assertIsNotNone(match_full)
        assert match is not None
        assert match_full is not None
        url = match_full.group(1)
        secret = match.group(1)
        generated_url = reverse(
            "account-confirm",
            kwargs={"user_id": user.pk, "secret": secret, "request_id": req.pk},
        )
        self.assertIn(generated_url, url)
        self.assertFalse(user.is_active)
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        req = FoiRequest.objects.get(pk=req.pk)
        mes = req.messages[0]
        mes.timestamp = mes.timestamp - timedelta(days=2)
        mes.save()
        self.assertEqual(req.status, "awaiting_response")
        self.assertEqual(req.visibility, 1)
        self.assertEqual(len(mail.outbox), 3)
        message = mail.outbox[1]
        self.assertIn(
            "Legal Note: This mail was sent through a Freedom Of Information Portal.",
            message.body,
        )
        self.assertIn(req.secret_address, message.extra_headers.get("Reply-To", ""))
        self.assertEqual(message.to[0], req.public_body.email)
        self.assertEqual(message.subject, "%s [#%s]" % (req.title, req.pk))
        resp = self.client.post(
            reverse("foirequest-set_status", kwargs={"slug": req.slug})
        )
        self.assertEqual(resp.status_code, 400)
        response = self.client.post(
            reverse("foirequest-set_law", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 400)
        new_foi_email = "foi@" + pb.email.split("@")[1]
        add_message_from_email(
            req,
            ParsedEmail(
                self.msgobj,
                **{
                    "date": timezone.now() - timedelta(days=1),
                    "subject": "Re: %s" % req.title,
                    "body": """Message""",
                    "html": None,
                    "from_": ("FoI Officer", new_foi_email),
                    "to": [(req.user.get_full_name(), req.secret_address)],
                    "cc": [],
                    "resent_to": [],
                    "resent_cc": [],
                    "attachments": [],
                }
            ),
        )
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertTrue(req.awaits_classification())
        self.assertEqual(len(req.messages), 2)
        self.assertEqual(req.messages[1].sender_email, new_foi_email)
        self.assertEqual(req.messages[1].sender_public_body, req.public_body)
        response = self.client.get(
            reverse("foirequest-show", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(req.status_settable)
        response = self.client.post(
            reverse("foirequest-set_status", kwargs={"slug": req.slug}),
            {"status": "invalid_status_settings_now"},
        )
        self.assertEqual(response.status_code, 400)
        costs = "123.45"
        status = "awaiting_response"
        response = self.client.post(
            reverse("foirequest-set_status", kwargs={"slug": req.slug}),
            {"status": status, "costs": costs},
        )
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.costs, float(costs))
        self.assertEqual(req.status, status)
        # send reply
        old_len = len(mail.outbox)
        response = self.client.post(
            reverse("foirequest-send_message", kwargs={"slug": req.slug}), {}
        )
        self.assertEqual(response.status_code, 400)

        post = {
            "sendmessage-message": "My custom reply",
            "sendmessage-address": user.address,
            "sendmessage-send_address": "1",
        }
        response = self.client.post(
            reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 400)

        post["sendmessage-to"] = "abc"
        response = self.client.post(
            reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 400)

        post["sendmessage-to"] = "9" * 10
        response = self.client.post(
            reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 400)

        pb_email = req.public_body.email
        req.public_body.email = ""
        req.public_body.save()
        post["sendmessage-to"] = pb_email
        post["sendmessage-subject"] = "Re: Custom subject"
        response = self.client.post(
            reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 400)
        req.public_body.email = pb_email
        req.public_body.save()

        post["sendmessage-subject"] = "Re: Custom subject"
        self.assertIn(new_foi_email, {x[0] for x in possible_reply_addresses(req)})
        post["sendmessage-to"] = new_foi_email
        response = self.client.post(
            reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 302)
        new_len = len(mail.outbox)
        self.assertEqual(old_len + 2, new_len)
        message = list(
            filter(
                lambda x: x.subject.startswith(post["sendmessage-subject"]), mail.outbox
            )
        )[-1]
        self.assertTrue(message.subject.endswith("[#%s]" % req.pk))
        self.assertTrue(message.body.startswith(post["sendmessage-message"]))
        self.assertIn(
            "Legal Note: This mail was sent through a Freedom Of Information Portal.",
            message.body,
        )
        self.assertIn(user.address, message.body)
        self.assertIn(new_foi_email, message.to[0])
        req._messages = None
        foimessage = list(req.messages)[-1]
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.last_message, foimessage.timestamp)
        self.assertEqual(foimessage.recipient_public_body, req.public_body)
        self.assertTrue(req.law.meta)
        other_laws = req.law.combined.all()

        response = self.client.post(
            reverse("foirequest-set_law", kwargs={"slug": req.slug}), {"law": "9" * 5}
        )
        self.assertEqual(response.status_code, 400)

        post = {"law": str(other_laws[0].pk)}
        response = self.client.post(
            reverse("foirequest-set_law", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(
            reverse("foirequest-show", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("foirequest-set_law", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 400)
        # logout
        self.client.logout()

        response = self.client.post(
            reverse("foirequest-set_law", kwargs={"slug": req.slug}), post
        )
        self.assertForbidden(response)

        response = self.client.post(
            reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
        )
        self.assertForbidden(response)
        response = self.client.post(
            reverse("foirequest-set_status", kwargs={"slug": req.slug}),
            {"status": status, "costs": costs},
        )
        self.assertForbidden(response)
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse("foirequest-set_law", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 403)

    def test_public_body_not_logged_in_request(self):
        self.client.logout()
        pb = PublicBody.objects.all()[0]
        response = self.client.post(
            reverse("foirequest-make_request"),
            {
                "subject": "Test-Subject",
                "body": "This is a test body",
                "user_email": "test@example.com",
                "publicbody": pb.pk,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFormError(
            response, "user_form", "first_name", ["This field is required."]
        )
        self.assertFormError(
            response, "user_form", "last_name", ["This field is required."]
        )

    def test_logged_in_request_with_public_body(self):
        pb = PublicBody.objects.all()[0]
        self.client.login(email="dummy@example.org", password="froide")
        post = {
            "subject": "Another Third Test-Subject",
            "body": "This is another test body",
            "publicbody": "bs",
            "public": "on",
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 400)
        post["law"] = str(pb.default_law.pk)
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 400)
        post["publicbody"] = "9" * 10  # not that many in fixture
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 400)
        post["publicbody"] = str(pb.pk)
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post["subject"])
        self.assertEqual(req.public_body.pk, pb.pk)
        self.assertTrue(req.messages[0].sent)
        self.assertEqual(req.law, pb.default_law)

        email_messages = list(
            filter(
                lambda x: req.secret_address in x.extra_headers.get("Reply-To", ""),
                mail.outbox,
            )
        )
        self.assertEqual(len(email_messages), 1)
        email_message = email_messages[0]
        self.assertEqual(email_message.to[0], pb.email)
        self.assertEqual(email_message.subject, "%s [#%s]" % (req.title, req.pk))
        self.assertEqual(
            email_message.extra_headers.get("Message-Id"),
            req.messages[0].make_message_id(),
        )

    def test_redirect_after_request(self):
        response = self.client.get(
            reverse("foirequest-make_request") + "?redirect=/speci4l-url/?blub=bla"
        )
        self.assertContains(response, 'value="/speci4l-url/?blub=bla"')

        pb = PublicBody.objects.all()[0]
        self.client.login(email="dummy@example.org", password="froide")

        post = {
            "subject": "Another Third Test-Subject",
            "body": "This is another test body",
            "redirect_url": "/foo/?blub=bla",
            "publicbody": str(pb.pk),
            "public": "on",
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post["subject"])
        self.assertIn("/foo/?", response["Location"])
        self.assertIn("blub=bla", response["Location"])
        self.assertIn("request=%s" % req.pk, response["Location"])

        post = {
            "subject": "Another fourth Test-Subject",
            "body": "This is another test body",
            "redirect_url": "http://evil.example.com",
            "publicbody": str(pb.pk),
            "public": "on",
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        request_sent = reverse("foirequest-request_sent")
        self.assertIn(request_sent, response["Location"])

    def test_redirect_after_request_new_account(self):
        pb = PublicBody.objects.all()[0]
        mail.outbox = []
        redirect_url = "/foo/?blub=bla"
        post = {
            "subject": "Another Third Test-Subject",
            "body": "This is another test body",
            "redirect_url": redirect_url,
            "publicbody": str(pb.pk),
            "public": "on",
            "first_name": "Stefan",
            "last_name": "Wehrmeyer",
            "address": "TestStreet 3\n55555 Town",
            "user_email": "sw@example.com",
            "reference": "foo:bar",
            "terms": "on",
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 302)
        account_new = reverse("account-new")
        self.assertIn(account_new, response["Location"])

        req = FoiRequest.objects.get(title=post["subject"])
        message = mail.outbox[0]
        self.assertEqual(message.to[0], post["user_email"])
        match = re.search(
            r"http://[\w:]+(/[\w/]+/\d+/%d/\w+/\S*)" % (req.pk), message.body
        )
        self.assertIsNotNone(match)
        url = match.group(1)
        response = self.client.get(url)
        self.assertIn("/foo/?", response["Location"])
        self.assertIn("blub=bla", response["Location"])
        self.assertIn("ref=foo%3Abar", response["Location"])
        self.assertIn("request=%s" % req.pk, response["Location"])

    def test_foi_email_settings(self):
        pb = PublicBody.objects.all()[0]
        self.client.login(email="dummy@example.org", password="froide")
        post = {
            "subject": "Another Third Test-Subject",
            "body": "This is another test body",
            "publicbody": str(pb.pk),
            "law": str(pb.default_law.pk),
            "public": "on",
        }

        def email_func(username, secret):
            return "email+%s@foi.example.com" % username

        with self.settings(
            FOI_EMAIL_FIXED_FROM_ADDRESS=False, FOI_EMAIL_TEMPLATE=email_func
        ):
            response = self.client.post(reverse("foirequest-make_request"), post)
            self.assertEqual(response.status_code, 302)
            req = FoiRequest.objects.get(title=post["subject"])
            self.assertTrue(req.messages[0].sent)
            addr = email_func(req.user.username, "")
            self.assertEqual(req.secret_address, addr)

    def test_logged_in_request_no_public_body(self):
        self.client.login(email="dummy@example.org", password="froide")
        user = User.objects.get(email="dummy@example.org")
        req = factories.FoiRequestFactory.create(
            user=user, status=FoiRequest.STATUS.PUBLICBODY_NEEDED, public_body=None
        )
        factories.FoiMessageFactory.create(request=req, sent=False)
        pb = PublicBody.objects.all()[0]

        other_req = FoiRequest.objects.filter(public_body__isnull=False)[0]
        response = self.client.post(
            reverse(
                "foirequest-suggest_public_body", kwargs={"slug": req.slug + "garbage"}
            ),
            {"publicbody": str(pb.pk)},
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            reverse("foirequest-suggest_public_body", kwargs={"slug": other_req.slug}),
            {"publicbody": str(pb.pk)},
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            reverse("foirequest-suggest_public_body", kwargs={"slug": req.slug}), {}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            reverse("foirequest-suggest_public_body", kwargs={"slug": req.slug}),
            {"publicbody": "9" * 10},
        )
        self.assertEqual(response.status_code, 400)
        self.client.logout()
        self.client.login(email="info@fragdenstaat.de", password="froide")
        mail.outbox = []
        response = self.client.post(
            reverse("foirequest-suggest_public_body", kwargs={"slug": req.slug}),
            {"publicbody": str(pb.pk), "reason": "A good reason"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            [t.public_body for t in req.publicbodysuggestion_set.all()], [pb]
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], req.user.email)
        response = self.client.post(
            reverse("foirequest-suggest_public_body", kwargs={"slug": req.slug}),
            {"publicbody": str(pb.pk), "reason": "A good reason"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            [t.public_body for t in req.publicbodysuggestion_set.all()], [pb]
        )
        self.assertEqual(len(mail.outbox), 1)

        # set public body
        response = self.client.post(
            reverse(
                "foirequest-set_public_body", kwargs={"slug": req.slug + "garbage"}
            ),
            {"suggestion": str(pb.pk)},
        )
        self.assertEqual(response.status_code, 404)
        self.client.logout()
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(
            reverse("foirequest-set_public_body", kwargs={"slug": req.slug}), {}
        )
        self.assertEqual(response.status_code, 400)
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertIsNone(req.public_body)

        response = self.client.post(
            reverse("foirequest-set_public_body", kwargs={"slug": req.slug}),
            {"suggestion": "9" * 10},
        )
        self.assertEqual(response.status_code, 400)
        self.client.logout()
        response = self.client.post(
            reverse("foirequest-set_public_body", kwargs={"slug": req.slug}),
            {"suggestion": str(pb.pk)},
        )
        self.assertForbidden(response)
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(
            reverse("foirequest-set_public_body", kwargs={"slug": req.slug}),
            {"suggestion": str(pb.pk)},
        )
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(pk=req.pk)
        message = req.foimessage_set.all()[0]
        self.assertIn(req.law.letter_start, message.plaintext)
        self.assertIn(req.law.letter_end, message.plaintext)
        self.assertEqual(req.public_body, pb)
        response = self.client.post(
            reverse("foirequest-set_public_body", kwargs={"slug": req.slug}),
            {"suggestion": str(pb.pk)},
        )
        self.assertEqual(response.status_code, 400)

    def test_postal_reply(self):
        self.client.login(email="info@fragdenstaat.de", password="froide")
        pb = PublicBody.objects.all()[0]
        post = {
            "subject": "Totally Random Request",
            "body": "This is another test body",
            "publicbody": str(pb.pk),
            "public": "on",
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post["subject"])
        response = self.client.get(
            reverse("foirequest-show", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 200)
        # Date message back
        message = req.foimessage_set.all()[0]
        message.timestamp = timezone.utc.localize(datetime(2011, 1, 1, 0, 0, 0))
        message.save()
        req.first_message = message.timestamp
        req.save()

        file_size = os.path.getsize(factories.TEST_PDF_PATH)
        post = QueryDict(mutable=True)
        post.update(
            {
                "postal_reply-date": "3000-01-01",  # far future
                "postal_reply-sender": "Some Sender",
                "postal_reply-subject": "",
                "postal_reply-text": "Some Text",
            }
        )

        self.client.logout()
        response = self.client.post(
            reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
        )
        self.assertForbidden(response)
        self.client.login(email="info@fragdenstaat.de", password="froide")

        pb = req.public_body
        req.public_body = None
        req.save()
        response = self.client.post(
            reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 400)
        req.public_body = pb
        req.save()

        response = self.client.post(
            reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
        )
        self.assertEqual(response.status_code, 400)
        post["postal_reply-date"] = "01/41garbl"
        response = self.client.post(
            reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
        )
        self.assertIn("postal_reply_form", response.context)
        self.assertEqual(response.status_code, 400)
        post["postal_reply-date"] = "2011-01-02"
        post["postal_reply-publicbody"] = str(pb.pk)
        post["postal_reply-text"] = ""
        with open(factories.TEST_PDF_PATH, "rb") as f:
            post["postal_reply-files"] = f
            response = self.client.post(
                reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
            )
        self.assertEqual(response.status_code, 302)

        message = req.foimessage_set.all()[1]

        attachment = message.foiattachment_set.all()[0]
        self.assertEqual(attachment.file.size, file_size)
        self.assertEqual(attachment.size, file_size)
        self.assertEqual(attachment.name, "test.pdf")

        # Change name in order to upload it again
        attachment.name = "other_test.pdf"
        attachment.save()

        postal_attachment_form = message.get_postal_attachment_form()
        self.assertTrue(postal_attachment_form)

        post = QueryDict(mutable=True)

        post_var = postal_attachment_form.add_prefix("files")

        with open(factories.TEST_PDF_PATH, "rb") as f:
            post.update({post_var: f})
            response = self.client.post(
                reverse(
                    "foirequest-add_postal_reply_attachment",
                    kwargs={"slug": req.slug, "message_id": "9" * 5},
                ),
                post,
            )

        self.assertEqual(response.status_code, 404)

        self.client.logout()
        with open(factories.TEST_PDF_PATH, "rb") as f:
            post.update({post_var: f})
            response = self.client.post(
                reverse(
                    "foirequest-add_postal_reply_attachment",
                    kwargs={"slug": req.slug, "message_id": message.pk},
                ),
                post,
            )
        self.assertForbidden(response)

        self.client.login(email="dummy@example.org", password="froide")
        with open(factories.TEST_PDF_PATH, "rb") as f:
            post.update({post_var: f})
            response = self.client.post(
                reverse(
                    "foirequest-add_postal_reply_attachment",
                    kwargs={"slug": req.slug, "message_id": message.pk},
                ),
                post,
            )

        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(email="info@fragdenstaat.de", password="froide")
        message = req.foimessage_set.all()[0]

        with open(factories.TEST_PDF_PATH, "rb") as f:
            post.update({post_var: f})
            response = self.client.post(
                reverse(
                    "foirequest-add_postal_reply_attachment",
                    kwargs={"slug": req.slug, "message_id": message.pk},
                ),
                post,
            )

        self.assertEqual(response.status_code, 400)

        message = req.foimessage_set.all()[1]
        response = self.client.post(
            reverse(
                "foirequest-add_postal_reply_attachment",
                kwargs={"slug": req.slug, "message_id": message.pk},
            )
        )
        self.assertEqual(response.status_code, 400)

        with open(factories.TEST_PDF_PATH, "rb") as f:
            post.update({post_var: f})
            response = self.client.post(
                reverse(
                    "foirequest-add_postal_reply_attachment",
                    kwargs={"slug": req.slug, "message_id": message.pk},
                ),
                post,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(message.foiattachment_set.all()), 2)

        # Adding the same document again should override the first one
        with open(factories.TEST_PDF_PATH, "rb") as f:
            post.update({post_var: f})
            response = self.client.post(
                reverse(
                    "foirequest-add_postal_reply_attachment",
                    kwargs={"slug": req.slug, "message_id": message.pk},
                ),
                post,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(message.foiattachment_set.all()), 2)

    def test_set_message_sender(self):
        from froide.foirequest.forms import get_message_sender_form

        mail.outbox = []
        self.client.login(email="dummy@example.org", password="froide")
        pb = PublicBody.objects.all()[0]
        post = {
            "subject": "A simple test request",
            "body": "This is another test body",
            "publicbody": str(pb.id),
            "public": "on",
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)
        req = FoiRequest.objects.get(title=post["subject"])
        add_message_from_email(
            req,
            ParsedEmail(
                self.msgobj,
                **{
                    "date": timezone.now() + timedelta(days=1),
                    "subject": "Re: %s" % req.title,
                    "body": """Message""",
                    "html": None,
                    "from_": ("FoI Officer", "randomfoi@example.com"),
                    "to": [(req.user.get_full_name(), req.secret_address)],
                    "cc": [],
                    "resent_to": [],
                    "resent_cc": [],
                    "attachments": [],
                }
            ),
        )
        req = FoiRequest.objects.get(title=post["subject"])
        self.assertEqual(len(req.messages), 2)
        self.assertEqual(len(mail.outbox), 3)
        notification = mail.outbox[-1]
        match = re.search(
            r"https?://[^/]+(/.*?/%d/[^\s]+)" % req.user.pk, notification.body
        )
        self.assertIsNotNone(match)
        url = match.group(1)
        self.client.logout()
        response = self.client.get(reverse("account-show"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        message = req.messages[1]
        self.assertIn(req.get_absolute_short_url(), response["Location"])
        response = self.client.get(reverse("account-requests"))
        self.assertEqual(response.status_code, 200)
        form = get_message_sender_form(foimessage=message)
        post_var = form.add_prefix("sender")
        self.assertTrue(message.is_response)
        original_pb = req.public_body
        alternate_pb = PublicBody.objects.all()[1]
        response = self.client.post(
            reverse(
                "foirequest-set_message_sender",
                kwargs={"slug": req.slug, "message_id": "9" * 8},
            ),
            {post_var: alternate_pb.id},
        )
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(message.sender_public_body, alternate_pb)

        self.client.logout()
        response = self.client.post(
            reverse(
                "foirequest-set_message_sender",
                kwargs={"slug": req.slug, "message_id": str(message.pk)},
            ),
            {post_var: alternate_pb.id},
        )
        self.assertForbidden(response)
        self.assertNotEqual(message.sender_public_body, alternate_pb)

        self.client.logout()
        self.client.login(email="dummy@example.org", password="froide")
        mes = req.messages[0]
        response = self.client.post(
            reverse(
                "foirequest-set_message_sender",
                kwargs={"slug": req.slug, "message_id": str(mes.pk)},
            ),
            {post_var: str(alternate_pb.id)},
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(message.sender_public_body, alternate_pb)

        response = self.client.post(
            reverse(
                "foirequest-set_message_sender",
                kwargs={"slug": req.slug, "message_id": message.pk},
            ),
            {post_var: "9" * 5},
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(message.sender_public_body, alternate_pb)

        response = self.client.post(
            reverse(
                "foirequest-set_message_sender",
                kwargs={"slug": req.slug, "message_id": message.pk},
            ),
            {post_var: str(alternate_pb.id)},
        )
        self.assertEqual(response.status_code, 302)
        message = FoiMessage.objects.get(pk=message.pk)
        self.assertEqual(message.sender_public_body, alternate_pb)

        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse(
                "foirequest-set_message_sender",
                kwargs={"slug": req.slug, "message_id": str(message.pk)},
            ),
            {post_var: original_pb.id},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(message.sender_public_body, original_pb)

    def test_apply_moderation(self):
        req = FoiRequest.objects.all()[0]
        self.assertTrue(req.is_foi)
        response = self.client.post(
            reverse("foirequest-apply_moderation", kwargs={"slug": req.slug + "-blub"}),
            data={"moderation_trigger": "nonfoi"},
        )
        self.assertEqual(response.status_code, 302)

        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(
            reverse("foirequest-apply_moderation", kwargs={"slug": req.slug + "-blub"}),
            data={"moderation_trigger": "nonfoi"},
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            reverse("foirequest-apply_moderation", kwargs={"slug": req.slug}),
            data={"moderation_trigger": "nonfoi"},
        )
        self.assertEqual(response.status_code, 403)

        req = FoiRequest.objects.get(pk=req.pk)
        self.assertTrue(req.is_foi)
        self.client.logout()
        self.client.login(email="moderator@example.org", password="froide")
        response = self.client.post(
            reverse("foirequest-apply_moderation", kwargs={"slug": req.slug}),
            data={"moderation_trigger": "nonfoi"},
        )
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertFalse(req.is_foi)

    def test_mark_not_foi_perm(self):
        req = FoiRequest.objects.all()[0]
        user = User.objects.get(email="dummy@example.org")
        content_type = ContentType.objects.get_for_model(FoiRequest)
        permission = Permission.objects.get(
            codename="mark_not_foi",
            content_type=content_type,
        )

        user.user_permissions.add(permission)

        self.assertTrue(req.is_foi)

        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(
            reverse("foirequest-apply_moderation", kwargs={"slug": req.slug}),
            data={"moderation_trigger": "nonfoi"},
        )
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertFalse(req.is_foi)

    def test_escalation_message(self):
        req = FoiRequest.objects.all()[0]
        attachments = list(generate_foirequest_files(req))
        req._messages = None  # Reset messages cache
        response = self.client.post(
            reverse("foirequest-escalation_message", kwargs={"slug": req.slug + "blub"})
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            reverse("foirequest-escalation_message", kwargs={"slug": req.slug})
        )
        self.assertForbidden(response)
        ok = self.client.login(email="dummy@example.org", password="froide")
        self.assertTrue(ok)
        response = self.client.post(
            reverse("foirequest-escalation_message", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 403)
        self.client.logout()
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse("foirequest-escalation_message", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 400)
        mail.outbox = []
        response = self.client.post(
            reverse("foirequest-escalation_message", kwargs={"slug": req.slug}),
            {
                "subject": "My Escalation Subject",
                "message": ("My Escalation Message" "\n%s\nDone" % req.get_auth_link()),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(req.get_absolute_url(), response["Location"])
        self.assertEqual(req.law.mediator, req.messages[-1].recipient_public_body)
        self.assertNotIn(req.get_auth_link(), req.messages[-1].plaintext_redacted)
        self.assertEqual(len(mail.outbox), 2)
        message = list(
            filter(lambda x: x.to[0] == req.law.mediator.email, mail.outbox)
        )[-1]
        self.assertEqual(message.attachments[0][0], "%s.pdf" % req.pk)
        self.assertEqual(message.attachments[0][2], "application/pdf")
        self.assertEqual(len(message.attachments), len(attachments))
        self.assertEqual(
            [x[0] for x in message.attachments], [x[0] for x in attachments]
        )

    def test_set_tags(self):
        req = FoiRequest.objects.all()[0]

        # Bad method
        response = self.client.get(
            reverse("foirequest-set_tags", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 405)

        # Bad slug
        response = self.client.post(
            reverse("foirequest-set_tags", kwargs={"slug": req.slug + "blub"})
        )
        self.assertEqual(response.status_code, 404)

        # Not logged in
        self.client.logout()
        response = self.client.post(
            reverse("foirequest-set_tags", kwargs={"slug": req.slug})
        )
        self.assertForbidden(response)

        # Not staff
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(
            reverse("foirequest-set_tags", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 403)

        # Bad form
        self.client.logout()
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse("foirequest-set_tags", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(req.tags.all()), 0)

        response = self.client.post(
            reverse("foirequest-set_tags", kwargs={"slug": req.slug}),
            {"tags": 'SomeTag, "Another Tag", SomeTag'},
        )
        self.assertEqual(response.status_code, 302)
        tags = req.tags.all()
        self.assertEqual(len(tags), 2)
        self.assertIn("SomeTag", [t.name for t in tags])
        self.assertIn("Another Tag", [t.name for t in tags])

    def test_set_summary(self):
        req = FoiRequest.objects.all()[0]

        # Bad method
        response = self.client.get(
            reverse("foirequest-set_summary", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 405)

        # Bad slug
        response = self.client.post(
            reverse("foirequest-set_summary", kwargs={"slug": req.slug + "blub"})
        )
        self.assertEqual(response.status_code, 404)

        # Not logged in
        self.client.logout()
        response = self.client.post(
            reverse("foirequest-set_summary", kwargs={"slug": req.slug})
        )
        self.assertForbidden(response)

        # Not user of request
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(
            reverse("foirequest-set_summary", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 403)

        # Request not final
        self.client.logout()
        self.client.login(email="info@fragdenstaat.de", password="froide")
        req.status = "awaiting_response"
        req.save()
        response = self.client.post(
            reverse("foirequest-set_summary", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 400)

        # No resolution given
        req.status = FoiRequest.STATUS.RESOLVED
        req.save()
        response = self.client.post(
            reverse("foirequest-set_summary", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 400)

        res = "This is resolved"
        response = self.client.post(
            reverse("foirequest-set_summary", kwargs={"slug": req.slug}),
            {"summary": res},
        )
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(id=req.id)
        self.assertEqual(req.summary, res)

    def test_approve_attachment(self):
        req = FoiRequest.objects.all()[0]
        mes = req.messages[-1]
        att = factories.FoiAttachmentFactory.create(belongs_to=mes, approved=False)

        # Bad method
        response = self.client.get(
            reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 405)

        # Bad slug
        response = self.client.post(
            reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": req.slug + "blub", "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 404)

        # Not logged in
        self.client.logout()
        response = self.client.post(
            reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertForbidden(response)

        # Not user of request
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(
            reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": req.slug, "attachment_id": "9" * 8},
            )
        )
        self.assertEqual(response.status_code, 404)

        user = User.objects.get(username="sw")
        user.is_staff = False
        user.save()

        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 302)
        att = FoiAttachment.objects.get(id=att.id)
        self.assertTrue(att.approved)

        att.approved = False
        att.can_approve = False
        att.save()
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 403)
        att = FoiAttachment.objects.get(id=att.id)
        self.assertFalse(att.approved)
        self.assertFalse(att.can_approve)

        self.client.logout()
        self.client.login(email="dummy_staff@example.org", password="froide")
        response = self.client.post(
            reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 302)
        att = FoiAttachment.objects.get(id=att.id)
        self.assertTrue(att.approved)
        self.assertFalse(att.can_approve)

    def test_delete_attachment(self):
        from froide.foirequest.models.attachment import DELETE_TIMEFRAME

        now = timezone.now()

        req = FoiRequest.objects.all()[0]
        mes = req.messages[-1]
        att = factories.FoiAttachmentFactory.create(
            belongs_to=mes, approved=False, timestamp=now
        )

        # Bad method
        response = self.client.get(
            reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 405)

        # Bad slug
        response = self.client.post(
            reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": req.slug + "blub", "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 404)

        # Not logged in
        self.client.logout()
        response = self.client.post(
            reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertForbidden(response)

        # Not user of request
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(
            reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": req.slug, "attachment_id": "9" * 8},
            )
        )
        self.assertEqual(response.status_code, 404)

        user = User.objects.get(username="sw")
        user.is_staff = False
        user.save()

        self.client.login(email="info@fragdenstaat.de", password="froide")

        # Don't allow deleting from non-postal messages
        mes.kind = "email"
        mes.save()
        response = self.client.post(
            reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 403)
        att_exists = FoiAttachment.objects.filter(id=att.id).exists()
        self.assertTrue(att_exists)

        mes.kind = "post"
        mes.save()

        att.can_approve = False
        att.save()

        response = self.client.post(
            reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 403)
        att_exists = FoiAttachment.objects.filter(id=att.id).exists()
        self.assertTrue(att_exists)

        att.can_approve = True
        att.save()

        response = self.client.post(
            reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 302)
        att_exists = FoiAttachment.objects.filter(id=att.id).exists()
        self.assertFalse(att_exists)

        att = factories.FoiAttachmentFactory.create(
            belongs_to=mes, approved=False, timestamp=now - DELETE_TIMEFRAME
        )

        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 403)
        att = FoiAttachment.objects.get(id=att.id)

        att = factories.FoiAttachmentFactory.create(
            belongs_to=mes, approved=False, timestamp=now
        )

        self.client.logout()
        self.client.login(email="dummy_staff@example.org", password="froide")
        response = self.client.post(
            reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": req.slug, "attachment_id": att.id},
            )
        )
        self.assertEqual(response.status_code, 302)
        att_exists = FoiAttachment.objects.filter(id=att.id).exists()
        self.assertFalse(att_exists)

    def test_make_same_request(self):
        req = FoiRequest.objects.all()[0]

        # req doesn't exist
        response = self.client.post(
            reverse("foirequest-make_same_request", kwargs={"slug": req.slug + "blub"})
        )
        self.assertEqual(response.status_code, 404)

        # message is publishable
        response = self.client.post(
            reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 302)

        req.not_publishable = True
        req.save()

        # not loged in, no form
        response = self.client.get(
            reverse("foirequest-show", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 200)

        mail.outbox = []
        user = User.objects.get(username="dummy")
        response = self.client.post(
            reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(FoiRequest.objects.filter(same_as=req, user=user).count(), 0)

        # user made original request
        self.client.login(email="info@fragdenstaat.de", password="froide")

        response = self.client.post(
            reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 400)

        req.same_as_count = 12000
        req.save()

        # make request
        self.client.logout()
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(
            reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)
        same_req = FoiRequest.objects.get(same_as=req, user=user)
        self.assertTrue(same_req.slug.endswith("-12001"))
        self.assertIn(same_req.get_absolute_url(), response["Location"])
        self.assertEqual(list(req.same_as_set), [same_req])
        self.assertEqual(same_req.identical_count(), 1)
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.identical_count(), 1)

        response = self.client.post(
            reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 400)
        same_req = FoiRequest.objects.get(same_as=req, user=user)

        self.client.logout()
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(
            reverse("foirequest-make_same_request", kwargs={"slug": same_req.slug})
        )
        self.assertEqual(response.status_code, 400)

        self.client.logout()
        mail.outbox = []
        post = {
            "first_name": "Bob",
            "last_name": "Bobbington",
            "address": "MyAddres 12\nB-Town",
            "user_email": "bob@example.com",
            "terms": "on",
        }
        response = self.client.post(
            reverse("foirequest-make_same_request", kwargs={"slug": same_req.slug}),
            post,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FoiRequest.objects.filter(same_as=req).count(), 2)
        same_req2 = FoiRequest.objects.get(same_as=req, user__email=post["user_email"])
        self.assertEqual(same_req2.status, "awaiting_user_confirmation")
        self.assertEqual(same_req2.visibility, 0)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to[0], post["user_email"])
        match = re.search(r"/(\d+)/%d/(\w+)/" % (same_req2.pk), message.body)
        self.assertIsNotNone(match)
        new_user = User.objects.get(id=int(match.group(1)))
        self.assertFalse(new_user.is_active)
        secret = match.group(2)
        response = self.client.get(
            reverse(
                "account-confirm",
                kwargs={
                    "user_id": new_user.pk,
                    "secret": secret,
                    "request_id": same_req2.pk,
                },
            )
        )
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(id=new_user.pk)
        self.assertTrue(new_user.is_active)
        same_req2 = FoiRequest.objects.get(pk=same_req2.pk)
        self.assertEqual(same_req2.status, "awaiting_response")
        self.assertEqual(same_req2.visibility, 2)
        self.assertEqual(len(mail.outbox), 3)

    def test_empty_costs(self):
        req = FoiRequest.objects.all()[0]
        user = User.objects.get(username="sw")
        req.status = "awaits_classification"
        req.user = user
        req.save()
        factories.FoiMessageFactory.create(status=None, request=req)
        self.client.login(email="info@fragdenstaat.de", password="froide")
        status = "awaiting_response"
        response = self.client.post(
            reverse("foirequest-set_status", kwargs={"slug": req.slug}),
            {"status": status, "costs": "", "resolution": ""},
        )
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.costs, 0.0)
        self.assertEqual(req.status, status)

    def test_resolution(self):
        req = FoiRequest.objects.all()[0]
        user = User.objects.get(username="sw")
        req.status = "awaits_classification"
        req.user = user
        req.save()
        mes = factories.FoiMessageFactory.create(status=None, request=req)
        self.client.login(email="info@fragdenstaat.de", password="froide")
        status = FoiRequest.STATUS.RESOLVED
        response = self.client.post(
            reverse("foirequest-set_status", kwargs={"slug": req.slug}),
            {"status": status, "costs": "", "resolution": ""},
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            reverse("foirequest-set_status", kwargs={"slug": req.slug}),
            {"status": status, "costs": "", "resolution": "bogus"},
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            reverse("foirequest-set_status", kwargs={"slug": req.slug}),
            {
                "status": status,
                "costs": "",
                "resolution": FoiRequest.RESOLUTION.SUCCESSFUL,
            },
        )
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(pk=req.pk)
        self.assertEqual(req.costs, 0.0)
        self.assertEqual(req.status, FoiRequest.STATUS.RESOLVED)
        self.assertEqual(req.resolution, FoiRequest.RESOLUTION.SUCCESSFUL)
        self.assertEqual(
            req.days_to_resolution(), (mes.timestamp - req.first_message).days
        )

    def test_search(self):
        pb = PublicBody.objects.all()[0]
        factories.rebuild_index()
        response = self.client.get(
            "%s?q=%s" % (reverse("foirequest-search"), pb.name[:6])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(quote(pb.name[:6]), response["Location"])

    def test_full_text_request(self):
        self.client.login(email="dummy@example.org", password="froide")
        pb = PublicBody.objects.all()[0]
        law = pb.default_law
        post = {
            "subject": "A Public Body Request",
            "body": "This is another test body with Ümläut€n",
            "full_text": "true",
            "publicbody": str(pb.id),
            "public": "on",
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title=post["subject"])
        message = req.foimessage_set.all()[0]
        self.assertIn(post["body"], message.plaintext)
        self.assertIn(post["body"], message.plaintext_redacted)
        self.assertNotIn(law.letter_start, message.plaintext)
        self.assertNotIn(law.letter_start, message.plaintext_redacted)
        self.assertNotIn(law.letter_end, message.plaintext)
        self.assertNotIn(law.letter_end, message.plaintext_redacted)

    def test_redaction_config(self):
        self.client.login(email="dummy@example.org", password="froide")
        req = FoiRequest.objects.all()[0]
        name = "Petra Radetzky"
        add_message_from_email(
            req,
            ParsedEmail(
                self.msgobj,
                **{
                    "date": timezone.now(),
                    "subject": "Reply",
                    "body": (
                        "Sehr geehrte Damen und Herren,\nblub\nbla\n\n"
                        "Mit freundlichen Grüßen\n" + name
                    ),
                    "html": "html",
                    "from_": (name, "petra.radetsky@bund.example.org"),
                    "to": [("", req.secret_address)],
                    "cc": [],
                    "resent_to": [],
                    "resent_cc": [],
                    "attachments": [],
                }
            ),
        )
        req = FoiRequest.objects.all()[0]
        last = req.messages[-1]
        self.assertNotIn(name, last.plaintext_redacted)
        form = get_send_message_form(
            {
                "sendmessage-to": req.public_body.email,
                "sendmessage-subject": "Testing",
                "sendmessage-address": "Address",
                "sendmessage-message": (
                    "Sehr geehrte Frau radetzky,"
                    "\n\nblub\n\nMit freundlichen Grüßen"
                    "\nStefan Wehrmeyer"
                ),
            },
            foirequest=req,
        )
        self.assertTrue(form.is_valid())
        form.save()

        req = FoiRequest.objects.all()[0]
        last = req.messages[-1]
        self.assertNotIn("radetzky", last.plaintext_redacted)

    def test_redaction_urls(self):
        from froide.foirequest.utils import redact_plaintext_with_request

        req = FoiRequest.objects.all()[0]
        url1 = "https://example.org/request/1231/upload/abcdef0123456789"
        url2 = "https://example.org/r/1231/auth/abcdef0123456789"
        url3 = "https://example.org/request/1231/auth/abcdef0123456789"
        plaintext = """Testing
            Really{url1}
            !!{url2}
            {url3}#also
        """.format(
            url1=url1, url2=url2, url3=url3
        )
        self.assertIn(url1, plaintext)
        self.assertIn(url2, plaintext)
        self.assertIn(url3, plaintext)

        redacted = redact_plaintext_with_request(plaintext, req)
        self.assertNotIn(url1, redacted)
        self.assertNotIn(url2, redacted)
        self.assertNotIn(url3, redacted)

    def test_empty_pb_email(self):
        self.client.login(email="info@fragdenstaat.de", password="froide")
        pb = PublicBody.objects.all()[0]
        pb.email = ""
        pb.save()
        response = self.client.get(
            reverse("foirequest-make_request", kwargs={"publicbody_slug": pb.slug})
        )
        self.assertEqual(response.status_code, 404)
        post = {
            "subject": "Test-Subject",
            "body": "This is a test body",
            "publicbody": str(pb.pk),
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 400)
        post = {
            "subject": "Test-Subject",
            "body": "This is a test body",
            "publicbody": str(pb.pk),
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 400)
        self.assertIn("publicbody", response.context["publicbody_form"].errors)
        self.assertEqual(len(response.context["publicbody_form"].errors), 1)

    @mock.patch(
        "froide.foirequest.views.attachment.redact_attachment_task.delay",
        lambda a, b, c: None,
    )
    def test_redact_attachment(self):
        foirequest = FoiRequest.objects.all()[0]
        message = foirequest.messages[0]
        att = factories.FoiAttachmentFactory.create(belongs_to=message)
        url = reverse(
            "foirequest-redact_attachment",
            kwargs={"slug": foirequest.slug, "attachment_id": "8" * 5},
        )

        self.assertIn(att.name, repr(att))

        response = self.client.get(url)
        self.assertForbidden(response)

        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        url = reverse(
            "foirequest-redact_attachment",
            kwargs={"slug": foirequest.slug, "attachment_id": str(att.id)},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, "[]", content_type="application/json")
        self.assertEqual(response.status_code, 200)

        old_att = FoiAttachment.objects.get(id=att.id)
        self.assertFalse(old_att.can_approve)
        # Redaction happens in background task, mocked away
        new_att = old_att.redacted
        self.assertTrue(new_att.is_redacted)
        self.assertFalse(new_att.approved)
        self.assertEqual(new_att.file, "")

    def test_extend_deadline(self):
        foirequest = FoiRequest.objects.all()[0]
        old_due_date = foirequest.due_date
        url = reverse("foirequest-extend_deadline", kwargs={"slug": foirequest.slug})
        post = {"time": ""}

        response = self.client.post(url, post)
        self.assertForbidden(response)

        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(url, post)
        self.assertEqual(response.status_code, 403)

        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(url, post)
        self.assertEqual(response.status_code, 400)

        response = self.client.post(url, {"time": 1000})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(url, {"time": -10})
        self.assertEqual(response.status_code, 400)

        post = {"time": "2"}
        response = self.client.post(url, post)
        self.assertEqual(response.status_code, 302)
        foirequest = FoiRequest.objects.get(id=foirequest.id)
        self.assertEqual(
            foirequest.due_date, foirequest.law.calculate_due_date(old_due_date, 2)
        )

    def test_resend_message(self):
        foirequest = FoiRequest.objects.all()[0]
        message = foirequest.messages[0]
        message.save()
        url = reverse(
            "foirequest-resend_message",
            kwargs={"slug": foirequest.slug, "message_id": message.id},
        )

        response = self.client.post(url)
        self.assertForbidden(response)

        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        self.client.login(email="moderator@example.org", password="froide")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

        DeliveryStatus.objects.create(
            message=message, status=DeliveryStatus.Delivery.STATUS_BOUNCED
        )
        self.assertTrue(message.can_resend_bounce)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        message = FoiMessage.objects.get(id=message.pk)
        ds = message.get_delivery_status()
        self.assertEqual(ds.status, DeliveryStatus.Delivery.STATUS_SENDING)

    def test_approve_message(self):
        foirequest = FoiRequest.objects.all()[0]
        message = foirequest.messages[0]
        message.content_hidden = True
        message.save()
        url = reverse(
            "foirequest-approve_message",
            kwargs={"slug": foirequest.slug, "message_id": message.pk},
        )

        response = self.client.post(url)
        self.assertForbidden(response)

        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        message = FoiMessage.objects.get(pk=message.pk)
        self.assertFalse(message.content_hidden)

    def test_too_long_subject(self):
        self.client.login(email="info@fragdenstaat.de", password="froide")
        pb = PublicBody.objects.all()[0]
        post = {
            "subject": "Test" * 64,
            "body": "This is another test body with Ümläut€n",
            "publicbody": pb.pk,
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 400)

        post = {
            "subject": "Test" * 55 + " a@b.de",
            "body": "This is another test body with Ümläut€n",
            "publicbody": pb.pk,
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 302)

    def test_remove_double_numbering(self):
        req = FoiRequest.objects.all()[0]
        form = get_send_message_form(
            {
                "sendmessage-to": req.public_body.email,
                "sendmessage-subject": req.title + " [#%s]" % req.pk,
                "sendmessage-message": "Test",
                "sendmessage-address": "Address",
            },
            foirequest=req,
        )
        self.assertTrue(form.is_valid())
        form.save()
        req = FoiRequest.objects.all()[0]
        last = req.messages[-1]
        self.assertEqual(last.subject.count("[#%s]" % req.pk), 1)

    @override_settings(FOI_EMAIL_FIXED_FROM_ADDRESS=False)
    def test_user_name_phd(self):
        from froide.helper.email_utils import make_address

        from_addr = make_address("j.doe.12345@example.org", "John Doe, Dr.")
        self.assertEqual(from_addr, '"John Doe, Dr." <j.doe.12345@example.org>')

    def test_throttling(self):
        froide_config = settings.FROIDE_CONFIG
        froide_config["request_throttle"] = [(2, 60), (5, 60 * 60)]

        pb = PublicBody.objects.all()[0]
        self.client.login(email="dummy@example.org", password="froide")

        with self.settings(FROIDE_CONFIG=froide_config):
            post = {
                "subject": "Another Third Test-Subject",
                "body": "This is another test body",
                "publicbody": str(pb.pk),
                "public": "on",
            }
            post["law"] = str(pb.default_law.pk)

            response = self.client.post(reverse("foirequest-make_request"), post)
            self.assertEqual(response.status_code, 302)

            response = self.client.post(reverse("foirequest-make_request"), post)
            self.assertEqual(response.status_code, 302)

            response = self.client.post(reverse("foirequest-make_request"), post)

            self.assertContains(
                response,
                "exceeded your request limit of 2 requests in 1",
                status_code=400,
            )

    def test_throttling_same_as(self):
        froide_config = settings.FROIDE_CONFIG
        froide_config["request_throttle"] = [(2, 60), (5, 60 * 60)]

        requests = []
        for i in range(3):
            requests.append(
                factories.FoiRequestFactory(
                    slug="same-as-request-%d" % i, not_publishable=True
                )
            )

        self.client.login(email="dummy@example.org", password="froide")

        with self.settings(FROIDE_CONFIG=froide_config):

            for i, req in enumerate(requests):
                response = self.client.post(
                    reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
                )
                if i < 2:
                    self.assertEqual(response.status_code, 302)

            self.assertContains(
                response,
                "exceeded your request limit of 2 requests in 1\xa0minute.",
                status_code=400,
            )

    def test_blocked_address(self):
        from froide.account.models import AccountBlocklist

        AccountBlocklist.objects.create(
            name="Address block test", address="Test(-| )Str 5.+Testtown"
        )
        req = FoiRequest.objects.all()[0]

        def make_form():
            return get_send_message_form(
                {
                    "sendmessage-to": req.public_body.email,
                    "sendmessage-subject": req.title,
                    "sendmessage-message": "Test",
                    "sendmessage-address": "Test-Str 5\nTesttown",
                },
                foirequest=req,
            )

        form = make_form()
        self.assertTrue(form.is_valid())

        # Set request user to normal user
        req.user = User.objects.get(email="dummy@example.org")
        form = make_form()
        self.assertFalse(form.is_valid())
        self.assertTrue("address" in form.errors)


class MediatorTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()
        self.msgobj = Parser().parse(BytesIO())

    def test_hiding_content(self):
        req = FoiRequest.objects.all()[0]
        mediator = req.law.mediator
        form = get_escalation_message_form(
            {"subject": "Escalate", "message": "Content"}, foirequest=req
        )
        self.assertTrue(form.is_valid())
        form.save()
        req = FoiRequest.objects.all()[0]
        add_message_from_email(
            req,
            ParsedEmail(
                self.msgobj,
                **{
                    "date": timezone.now(),
                    "subject": "Reply",
                    "body": "Content",
                    "html": "html",
                    "from_": ("Name", mediator.email),
                    "to": [("", req.secret_address)],
                    "cc": [],
                    "resent_to": [],
                    "resent_cc": [],
                    "attachments": [],
                }
            ),
        )
        req = FoiRequest.objects.all()[0]
        last = req.messages[-1]
        self.assertTrue(last.content_hidden)

    def test_no_public_body(self):
        user = User.objects.get(username="sw")
        req = factories.FoiRequestFactory.create(
            user=user, public_body=None, status="public_body_needed", site=self.site
        )
        req.save()
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.get(req.get_absolute_url())
        self.assertNotContains(response, "Mediation")
        response = self.client.post(
            reverse("foirequest-escalation_message", kwargs={"slug": req.slug})
        )
        self.assertEqual(response.status_code, 400)
        message = list(response.context["messages"])[0]
        self.assertIn("cannot be escalated", message.message)


class JurisdictionTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()
        self.pb = PublicBody.objects.filter(jurisdiction__slug="nrw")[0]

    def test_letter_public_body(self):
        self.client.login(email="info@fragdenstaat.de", password="froide")
        post = {
            "subject": "Jurisdiction-Test-Subject",
            "body": "This is a test body",
            "publicbody": self.pb.pk,
        }
        response = self.client.post(reverse("foirequest-make_request"), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.get(title="Jurisdiction-Test-Subject")
        law = FoiLaw.objects.get(meta=True, jurisdiction__slug="nrw")
        self.assertEqual(req.law, law)
        mes = req.messages[0]
        self.assertIn(law.letter_end, mes.plaintext)


class PackageFoiRequestTest(TestCase):
    def setUp(self):
        factories.make_world()

    def test_package(self):
        fr = FoiRequest.objects.all()[0]
        bytes = package_foirequest(fr)
        zfile = zipfile.ZipFile(BytesIO(bytes), "r")
        filenames = [
            r"%s/%s\.pdf" % (fr.pk, fr.pk),
            r"%s/20\d{2}-\d{2}-\d{2}_1-file_\d+\.pdf" % fr.pk,
            r"%s/20\d{2}-\d{2}-\d{2}_1-file_\d+\.pdf" % fr.pk,
        ]
        zip_names = zfile.namelist()
        self.assertEqual(len(filenames), len(zip_names))
        for zname, fname in zip(zip_names, filenames):
            self.assertTrue(bool(re.match(r"^%s$" % fname, zname)))
