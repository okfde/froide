import json
import os
from datetime import datetime

from django.conf import settings
from django.core import mail
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from froide.foirequest.foi_mail import add_message_from_email
from froide.foirequest.models import DeferredMessage, FoiMessage, FoiRequest
from froide.foirequest.services import BOUNCE_TAG
from froide.foirequest.tasks import process_mail
from froide.foirequest.tests import factories
from froide.helper.email_parsing import parse_email
from froide.problem.models import ProblemReport

TEST_DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "testdata"))


def p(path: str) -> str:
    return os.path.join(TEST_DATA_ROOT, path)


class MailTestMixin:
    def setUp(self):
        self.secret_address = "sw+yurpykc1hr@fragdenstaat.de"
        site = factories.make_world()
        date = datetime(2010, 6, 5, 5, 54, 40, tzinfo=timezone.utc)
        req = factories.FoiRequestFactory.create(
            site=site,
            secret_address=self.secret_address,
            first_message=date,
            last_message=date,
        )
        factories.FoiMessageFactory.create(request=req, timestamp=date)


class MailTransactionTest(MailTestMixin, TransactionTestCase):
    def test_working_with_attachment(self):
        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        domain = request.public_body.email.split("@")[1]
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 1)
        with open(p("test_mail_02.txt"), "rb") as f:
            mail_string = f.read().replace(
                b"abcd@me.com", b"abcde@" + domain.encode("ascii")
            )
            process_mail.delay(mail_string)

        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        self.assertEqual(
            messages[1].subject,
            "Fwd: Informationsfreiheitsgesetz des Bundes, Antragsvordruck für Open Data",
        )
        self.assertEqual(len(messages[1].attachments), 2)
        self.assertEqual(messages[1].attachments[0].name, "TI-IFG-AntragVordruck.docx")
        self.assertTrue(messages[1].attachments[1].name.endswith(".pdf"))
        self.assertFalse(messages[1].attachments[0].is_converted)
        self.assertTrue(messages[1].attachments[1].is_converted)
        self.assertTrue(messages[1].attachments[1].converted is None)
        self.assertEqual(
            messages[1].attachments[0].converted, messages[1].attachments[1]
        )


class MailTest(MailTestMixin, TestCase):
    def test_working(self):
        with open(p("test_mail_01.txt"), "rb") as f:
            process_mail.delay(f.read())
        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        messages = request.messages
        self.assertEqual(len(messages), 2)
        self.assertIn("Jörg Gahl-Killen", [m.sender_name for m in messages])
        message = messages[1]
        self.assertEqual(
            message.timestamp, datetime(2010, 7, 5, 5, 54, 40, tzinfo=timezone.utc)
        )
        self.assertEqual(
            message.subject,
            "Anfrage nach dem Informationsfreiheitsgesetz;  Förderanträge und Verwendungsnachweise der Hanns-Seidel-Stiftung;  Vg. 375-2018",
        )
        self.assertEqual(message.recipient, request.user.display_name())
        self.assertEqual(message.recipient_email, "sw+yurpykc1hr@fragdenstaat.de")

    def test_wrong_address(self):
        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        request.delete()
        mail.outbox = []
        with open(p("test_mail_01.txt"), "rb") as f:
            process_mail.delay(f.read())
        self.assertEqual(len(mail.outbox), len(settings.MANAGERS))
        self.assertTrue(
            all([_("Unknown FoI-Mail Recipient") in m.subject for m in mail.outbox])
        )
        recipients = [m.to[0] for m in mail.outbox]
        for manager in settings.MANAGERS:
            self.assertIn(manager[1], recipients)

    def test_inline_attachments(self):
        with open(p("test_mail_03.txt"), "rb") as f:
            email = parse_email(f)
        self.assertEqual(len(email.attachments), 1)
        self.assertEqual(email.subject, "Öffentlicher Personennahverkehr")

    def test_long_attachment_names(self):
        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        with open(p("test_mail_04.txt"), "rb") as f:
            mail = parse_email(f)
        self.assertEqual(
            mail.subject,
            "Kooperationen des Ministerium für Schule und "
            "Weiterbildung des Landes Nordrhein-Westfalen mit außerschulischen Partnern",
        )
        self.assertEqual(
            mail.attachments[0].name,
            "Kooperationen des MSW, Antrag "
            "nach Informationsfreiheitsgesetz NRW, Stefan Safario vom 06.12.2012 - AW vom "
            "08.01.2013 - RS.pdf",
        )
        add_message_from_email(request, mail)
        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1].subject, mail.subject)
        self.assertEqual(len(messages[1].attachments), 2)
        names = set([a.name for a in messages[1].attachments])
        self.assertEqual(
            names,
            set(
                [
                    "KooperationendesMSWAntragnachInformationsfreiheitsgesetzNRWStefanSafariovom06.12.2012-Anlage.pdf",
                    "KooperationendesMSWAntragnachInformationsfreiheitsgesetzNRWStefanSafariovom06.12.2012-AWvom08.01.2013-RS.pdf",
                ]
            ),
        )

    def test_recipient_parsing(self):
        with open(p("test_mail_05.txt"), "rb") as f:
            mail = parse_email(f)
        self.assertEqual(len(mail.cc), 2)
        self.assertEqual(len(mail.to), 2)
        self.assertEqual(len(mail.x_original_to), 1)
        self.assertTrue(mail.is_auto_reply)

    def test_strip_html(self):
        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        with open(p("test_mail_05.txt"), "rb") as f:
            mail = parse_email(f)
        add_message_from_email(request, mail)
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        mes = messages[1]
        self.assertTrue(len(mes.plaintext_redacted) > 0)
        self.assertTrue(len(mes.plaintext) > 0)

    def test_attachment_name_broken_encoding(self):
        with open(p("test_mail_06.txt"), "rb") as f:
            mail = parse_email(f)
        self.assertEqual(len(mail.attachments), 2)
        self.assertEqual(
            mail.attachments[0].name,
            "usernameEingangsbestätigung und Hinweis auf Unzustellbarkeit - Username.pdf",
        )
        self.assertEqual(mail.attachments[1].name, "15-725_002 II_0367.pdf")

    def test_attachment_name_redaction(self):
        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        user = factories.UserFactory.create(last_name="Username")
        user.private = True
        user.save()
        request.user = user
        request.save()
        with open(p("test_mail_06.txt"), "rb") as f:
            mail = parse_email(f)
        self.assertEqual(len(mail.attachments), 2)
        self.assertEqual(
            mail.attachments[0].name,
            "usernameEingangsbestätigung und Hinweis auf Unzustellbarkeit - Username.pdf",
        )
        add_message_from_email(request, mail)
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        mes = messages[1]
        self.assertIn(
            "NAMEEingangsbesttigungundHinweisaufUnzustellbarkeit-NAME.pdf",
            {a.name for a in mes.attachments},
        )

    def test_attachment_name_parsing(self):
        with open(p("test_mail_07.txt"), "rb") as f:
            mail = parse_email(f)
        self.assertEqual(
            mail.subject,
            "Anfrage nach dem Informationsfreiheitsgesetz; Gespräch damaliger BM Steinmeier Matthias Müller VW AG; Vg. 069-2018",
        )
        self.assertEqual(len(mail.attachments), 3)
        self.assertEqual(mail.attachments[0].name, "Bescheid Fäker.pdf")
        self.assertEqual(
            mail.attachments[1].name,
            "180328 Schreiben an Antragstellerin; Vg. 069-2018.pdf",
        )
        self.assertEqual(
            mail.attachments[2].name, "Müller_Michael_Metrobus 6_7_8_26.xlsx"
        )

    def test_attachment_name_parsing_2(self):
        with open(p("test_mail_11.txt"), "rb") as f:
            mail = parse_email(f)
        self.assertEqual(
            mail.subject,
            "Bescheid zu Ihrer ergänzten IFG-Anfrage Bestellung Infomaterial, Broschüren... [#32154]",
        )
        self.assertEqual(len(mail.attachments), 1)
        self.assertEqual(mail.attachments[0].name, "20180904_Bescheid Broschüren.pdf")

    def test_address_list(self):
        with open(p("test_mail_01.txt"), "rb") as f:
            mail = parse_email(f)
        self.assertEqual(len(mail.cc), 5)

    @override_settings(FOI_EMAIL_DOMAIN=["fragdenstaat.de", "example.com"])
    def test_additional_domains(self):
        with open(p("test_mail_01.txt"), "rb") as f:
            process_mail.delay(f.read().replace(b"@fragdenstaat.de", b"@example.com"))
        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        messages = request.messages
        self.assertEqual(len(messages), 2)
        self.assertIn("Jörg Gahl-Killen", [m.sender_name for m in messages])
        message = messages[1]
        self.assertEqual(
            message.timestamp, datetime(2010, 7, 5, 5, 54, 40, tzinfo=timezone.utc)
        )

    def test_eml_attachments(self):
        with open(p("test_mail_08.txt"), "rb") as f:
            mail = parse_email(f)
        subject = "WG: Disziplinarverfahren u.a. gegen Bürgermeister/Hauptverwaltungsbeamte/Amtsdirektoren/ehrenamtliche Bürgermeister/Ortsvorsteher/Landräte im Land Brandenburg in den letzten Jahren [#5617]"
        self.assertEqual(mail.attachments[0].name, "%s.eml" % subject[:45])

    def test_missing_date(self):
        with open(p("test_mail_08.txt"), "rb") as f:
            process_mail.delay(f.read())
        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        messages = request.messages
        self.assertEqual(len(messages), 2)
        message = messages[1]
        self.assertEqual(message.timestamp.date(), timezone.now().date())

    def test_borked_subject(self):
        """Subject completly borked"""
        with open(p("test_mail_09.txt"), "rb") as f:
            mail = parse_email(f)
        self.assertIn("Unterlagen nach", mail.subject)
        self.assertIn("E-Mail Empfangsbest", mail.subject)

    def test_attachment_name_parsing_header(self):
        with open(p("test_mail_10.txt"), "rb") as f:
            mail = parse_email(f)
        self.assertEqual(len(mail.attachments), 1)
        self.assertEqual(
            mail.attachments[0].name, "Eingangsbestätigung Akteneinsicht.doc"
        )

    def test_html_only_mail(self):
        with open(p("test_mail_13.txt"), "rb") as f:
            mail = parse_email(f)

        self.assertTrue(len(mail.body) > 10)
        # Markdown like links are rendered
        self.assertIn(" ( https://", mail.body)
        self.assertIn("*peter.mueller@kreis-steinfurt.de*", mail.body)


class DeferredMessageTest(TestCase):
    def setUp(self):
        self.secret_address = "sw+yurpykc1hr@fragdenstaat.de"
        self.site = factories.make_world()
        self.req = factories.FoiRequestFactory.create(
            site=self.site, secret_address=self.secret_address
        )
        self.other_req = factories.FoiRequestFactory.create(
            site=self.site, secret_address="sw+abcsd@fragdenstaat.de"
        )
        factories.FoiMessageFactory.create(request=self.req)

    def test_deferred(self):
        count_messages = len(self.req.get_messages())
        name, domain = self.req.secret_address.split("@")
        bad_mail = "@".join((name + "x", domain))
        with open(p("test_mail_01.txt"), "rb") as f:
            mail = f.read().decode("ascii")
        mail = mail.replace(self.secret_address, bad_mail)
        process_mail.delay(mail.encode("ascii"))
        self.assertEqual(
            count_messages, FoiMessage.objects.filter(request=self.req).count()
        )
        dms = DeferredMessage.objects.filter(recipient=bad_mail)
        self.assertEqual(len(dms), 1)
        dm = dms[0]
        dm.redeliver(self.req)
        req = FoiRequest.objects.get(id=self.req.id)
        self.assertEqual(len(req.messages), count_messages + 1)
        dm = DeferredMessage.objects.get(id=dm.id)
        self.assertEqual(dm.request, req)

    def test_double_deferred(self):
        count_messages = len(self.req.get_messages())
        name, domain = self.req.secret_address.split("@")
        bad_mail = "@".join((name + "x", domain))
        with open(p("test_mail_01.txt"), "rb") as f:
            mail = f.read().decode("ascii")
        mail = mail.replace(self.secret_address, bad_mail)
        self.assertEqual(DeferredMessage.objects.count(), 0)

        # there is one deferredmessage matching, so deliver to associated request
        DeferredMessage.objects.create(recipient=bad_mail, request=self.req)
        process_mail.delay(mail.encode("ascii"))
        self.assertEqual(
            count_messages + 1, FoiMessage.objects.filter(request=self.req).count()
        )
        self.assertEqual(DeferredMessage.objects.count(), 1)

        # there is more than one deferredmessage matching
        # So delivery is ambiguous, create deferred message instead
        DeferredMessage.objects.create(recipient=bad_mail, request=self.other_req)
        process_mail.delay(mail.encode("ascii"))
        self.assertEqual(
            count_messages + 1, FoiMessage.objects.filter(request=self.req).count()
        )
        self.assertEqual(DeferredMessage.objects.count(), 3)


class SpamMailTest(TestCase):
    def setUp(self):
        self.secret_address = "sw+yurpykc1hr@fragdenstaat.de"
        self.site = factories.make_world()
        self.req = factories.FoiRequestFactory.create(
            site=self.site, secret_address=self.secret_address
        )
        factories.FoiMessageFactory.create(request=self.req)
        factories.FoiMessageFactory.create(request=self.req, is_response=True)

    @override_settings(MANAGERS=[("Name", "manager@example.com")])
    def test_spam(self):
        mail.outbox = []

        count_messages = len(self.req.get_messages())
        name, domain = self.req.secret_address.split("@")
        recipient = self.secret_address
        with open(p("test_mail_01.txt"), "rb") as f:
            email = (
                f.read().decode("ascii").replace("hb@example.com", "hb@bad-example.com")
            )
        process_mail.delay(email.encode("ascii"))
        self.assertEqual(
            count_messages, FoiMessage.objects.filter(request=self.req).count()
        )
        dms = DeferredMessage.objects.filter(recipient=recipient, spam=None)
        self.assertEqual(len(dms), 1)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(MANAGERS=[("Name", "manager@example.com")])
    def test_existing_spam(self):
        mail.outbox = []

        count_messages = len(self.req.get_messages())
        name, domain = self.req.secret_address.split("@")
        recipient = self.secret_address
        sender = "hb@bad-example.com"
        DeferredMessage.objects.create(recipient=recipient, spam=True, sender=sender)
        with open(p("test_mail_01.txt"), "rb") as f:
            email = f.read().decode("ascii").replace("hb@example.com", sender)
        process_mail.delay(email.encode("ascii"))
        # New mail is dropped, not even stored in deferred
        self.assertEqual(
            count_messages, FoiMessage.objects.filter(request=self.req).count()
        )
        dms = DeferredMessage.objects.filter(sender=sender, spam=True)
        self.assertEqual(len(dms), 1)
        self.assertEqual(len(mail.outbox), 0)


class BounceMailTest(TestCase):
    def setUp(self):
        self.secret_address = "sw+yurpykc1hr@fragdenstaat.de"
        self.site = factories.make_world()
        self.req = factories.FoiRequestFactory.create(
            site=self.site, secret_address=self.secret_address
        )
        factories.FoiMessageFactory.create(
            timestamp=timezone.now().replace(2012, 1, 1),
            request=self.req,
            recipient_email="nonexistant@example.org",
        )

    @override_settings(MANAGERS=[("Name", "manager@example.com")])
    def test_bounce(self):
        mail.outbox = []

        with open(p("test_mail_12.txt"), "rb") as f:
            process_mail.delay(f.read())

        req = FoiRequest.objects.get(pk=self.req.pk)
        bounce_message = req.messages[-1]
        self.assertEqual(bounce_message.original, req.messages[0])
        tags = bounce_message.tags.all().values_list("name", flat=True)
        self.assertIn(BOUNCE_TAG, tags)
        self.assertTrue(
            ProblemReport.objects.filter(message=bounce_message.original).exists()
        )


class ClosedRequestTest(TestCase):
    def setUp(self):
        self.secret_address = "sw+yurpykc1hr@fragdenstaat.de"
        self.site = factories.make_world()
        self.req = factories.FoiRequestFactory.create(
            site=self.site, secret_address=self.secret_address, closed=True
        )
        factories.FoiMessageFactory.create(request=self.req)
        factories.FoiMessageFactory.create(request=self.req, is_response=True)

    def test_closed(self):
        count_messages = len(self.req.get_messages())
        name, domain = self.req.secret_address.split("@")
        recipient = self.secret_address
        with open(p("test_mail_01.txt"), "rb") as f:
            mail = f.read()
        process_mail.delay(mail)
        self.assertEqual(
            count_messages, FoiMessage.objects.filter(request=self.req).count()
        )
        dms = DeferredMessage.objects.filter(recipient=recipient)
        self.assertEqual(len(dms), 0)


class PostMarkMailTest(TestCase):
    def setUp(self):
        self.secret_address = "sw+yurpykc1hr@fragdenstaat.de"
        self.site = factories.make_world()
        date = datetime(2010, 6, 5, 5, 54, 40, tzinfo=timezone.utc)
        req = factories.FoiRequestFactory.create(
            site=self.site,
            secret_address=self.secret_address,
            first_message=date,
            last_message=date,
        )
        factories.FoiMessageFactory.create(request=req, timestamp=date)
        self.post_data = {
            "From": "myUser@example.com",
            "FromFull": {"Email": "myUser@example.com", "Name": "John Doe"},
            "To": self.secret_address,
            "ToFull": [{"Email": self.secret_address, "Name": ""}],
            "Cc": '"Full name" <sample.cc@example.com>, "Another Cc" <another.cc@example.com>',
            "CcFull": [
                {"Email": "sample.cc@example.com", "Name": "Full name"},
                {"Email": "another.cc@example.com", "Name": "Another Cc"},
            ],
            "ReplyTo": "myUsersReplyAddress@example.com",
            "Subject": "This is an inbound message",
            "MessageID": "22c74902-a0c1-4511-804f2-341342852c90",
            "Date": "Thu, 5 Apr 2012 16:59:01 +0200",
            "MailboxHash": "ahoy",
            "TextBody": "[ASCII]",
            "HtmlBody": "[HTML(encoded)]",
            "Tag": "",
            "Headers": [
                {
                    "Name": "X-Spam-Checker-Version",
                    "Value": "SpamAssassin 3.3.1 (2010-03-16) onrs-ord-pm-inbound1.wildbit.com",
                },
                {"Name": "X-Spam-Status", "Value": "No"},
                {"Name": "X-Spam-Score", "Value": "-0.1"},
                {
                    "Name": "X-Spam-Tests",
                    "Value": "DKIM_SIGNED,DKIM_VALID,DKIM_VALID_AU,SPF_PASS",
                },
                {
                    "Name": "Received-SPF",
                    "Value": "Pass (sender SPF authorized) identity=mailfrom; client-ip=209.85.160.180; helo=mail-gy0-f180.google.com; envelope-from=myUser@theirDomain.com; receiver=451d9b70cf9364d23ff6f9d51d870251569e+ahoy@inbound.postmarkapp.com",
                },
                {
                    "Name": "DKIM-Signature",
                    "Value": "v=1; a=rsa-sha256; c=relaxed/relaxed;                d=wildbit.com; s=google;                h=mime-version:reply-to:date:message-id:subject:from:to:cc                 :content-type;                bh=cYr/+oQiklaYbBJOQU3CdAnyhCTuvemrU36WT7cPNt0=;                b=QsegXXbTbC4CMirl7A3VjDHyXbEsbCUTPL5vEHa7hNkkUTxXOK+dQA0JwgBHq5C+1u                 iuAJMz+SNBoTqEDqte2ckDvG2SeFR+Edip10p80TFGLp5RucaYvkwJTyuwsA7xd78NKT                 Q9ou6L1hgy/MbKChnp2kxHOtYNOrrszY3JfQM=",
                },
                {"Name": "MIME-Version", "Value": "1.0"},
                {
                    "Name": "Message-ID",
                    "Value": "<CAGXpo2WKfxHWZ5UFYCR3H_J9SNMG+5AXUovfEFL6DjWBJSyZaA@mail.example.com>",
                },
            ],
            "Attachments": [
                {
                    "Name": "myimage.png",
                    "Content": "[BASE64-ENCODED CONTENT]",
                    "ContentType": "image/png",
                    "ContentLength": 4096,
                    "ContentID": "myimage.png@01CE7342.75E71F80",
                },
                {
                    "Name": "mypaper.doc",
                    "Content": "[BASE64-ENCODED CONTENT]",
                    "ContentType": "application/msword",
                    "ContentLength": 16384,
                    "ContentID": "",
                },
            ],
        }

    def test_postmark_post(self, url=None):
        if url is None:
            url = reverse("foirequest-postmark_inbound")
        response = self.client.post(
            url,
            json.dumps(self.post_data).encode("utf-8"),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        request = FoiRequest.objects.get_by_secret_mail(self.secret_address)
        mes = request.messages[-1]
        self.assertEqual(mes.sender_email, "myUser@example.com")

    def test_postmark_bounce(self):
        self.test_postmark_post(url=reverse("foirequest-postmark_bounce"))
