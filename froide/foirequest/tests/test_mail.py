# -*- coding: utf-8 -*-
from __future__ import with_statement

from datetime import datetime
import json
import os

from django.test import TestCase
from django.core import mail
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.utils.six import BytesIO
from django.core.urlresolvers import reverse

from froide.helper.email_utils import EmailParser

from froide.foirequest.tasks import process_mail
from froide.foirequest.models import (FoiRequest, FoiMessage, DeferredMessage)
from froide.foirequest.tests import factories

TEST_DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'testdata'))


def p(path):
    return os.path.join(TEST_DATA_ROOT, path)


class MailTest(TestCase):
    def setUp(self):
        site = factories.make_world()
        date = datetime(2010, 6, 5, 5, 54, 40, tzinfo=timezone.utc)
        req = factories.FoiRequestFactory.create(site=site,
            secret_address="sw+yurpykc1hr@fragdenstaat.de",
            first_message=date, last_message=date)
        factories.FoiMessageFactory.create(request=req, timestamp=date)

    def test_working(self):
        with open(p("test_mail_01.txt"), 'rb') as f:
            process_mail.delay(f.read())
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        messages = request.messages
        self.assertEqual(len(messages), 2)
        self.assertIn(u'J\xf6rg Gahl-Killen', [m.sender_name for m in messages])
        message = messages[1]
        self.assertEqual(message.timestamp,
                datetime(2010, 7, 5, 5, 54, 40, tzinfo=timezone.utc))

    def test_working_with_attachment(self):
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 1)

        with open(p("test_mail_02.txt"), 'rb') as f:
            process_mail.delay(f.read())

        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1].subject, u"Fwd: Informationsfreiheitsgesetz des Bundes, Antragsvordruck für Open Data")
        self.assertEqual(len(messages[1].attachments), 2)
        self.assertEqual(messages[1].attachments[0].name,
                         u"TI-IFG-AntragVordruck.docx")
        self.assertTrue(messages[1].attachments[1].name.endswith(u".pdf"))
        self.assertFalse(messages[1].attachments[0].is_converted)
        self.assertTrue(messages[1].attachments[1].is_converted)
        self.assertTrue(messages[1].attachments[1].converted is None)
        self.assertEqual(
            messages[1].attachments[0].converted,
            messages[1].attachments[1]
        )

    def test_wrong_address(self):
        request = FoiRequest.objects.get_by_secret_mail(
                u"sw+yurpykc1hr@fragdenstaat.de")
        request.delete()
        mail.outbox = []
        with open(p("test_mail_01.txt"), 'rb') as f:
            process_mail.delay(f.read())
        self.assertEqual(len(mail.outbox), len(settings.MANAGERS))
        self.assertTrue(all([_('Unknown FoI-Mail Recipient') in m.subject for m in mail.outbox]))
        recipients = [m.to[0] for m in mail.outbox]
        for manager in settings.MANAGERS:
            self.assertIn(manager[1], recipients)

    def test_inline_attachments(self):
        parser = EmailParser()
        with open(p("test_mail_03.txt"), 'rb') as f:
            email = parser.parse(f)
        self.assertEqual(len(email['attachments']), 1)

    def test_long_attachment_names(self):
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        with open(p("test_mail_04.txt"), 'rb') as f:
            parser = EmailParser()
            content = f.read()
            mail = parser.parse(BytesIO(content))
        self.assertEqual(mail['subject'], u'Kooperationen des Ministerium für Schule und '
                u'Weiterbildung des Landes Nordrhein-Westfalen mit außerschulischen Partnern')
        self.assertEqual(mail['attachments'][0].name, u'Kooperationen des MSW, Antrag '
                'nach Informationsfreiheitsgesetz NRW, Stefan Safario vom 06.12.2012 - AW vom '
                '08.01.2013 - RS.pdf')
        request.add_message_from_email(mail, content)
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1].subject, mail['subject'])
        self.assertEqual(len(messages[1].attachments), 2)
        self.assertEqual(messages[1].attachments[0].name, u"KooperationendesMSWAntragnachInformationsfreiheitsgesetzNRWStefanSafariovom06.12.2012-AWvom08.01.2013-RS.pdf")

    def test_strip_html(self):
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        with open(p("test_mail_05.txt"), 'rb') as f:
            parser = EmailParser()
            content = f.read()
            mail = parser.parse(BytesIO(content))
        request.add_message_from_email(mail, content)
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        mes = messages[1]
        self.assertTrue(len(mes.plaintext_redacted) > 0)
        self.assertTrue(len(mes.plaintext) > 0)

    def test_attachment_name_broken_encoding(self):
        with open(p("test_mail_06.txt"), 'rb') as f:
            parser = EmailParser()
            content = f.read()
            mail = parser.parse(BytesIO(content))
            self.assertEqual(len(mail['attachments']), 1)
            self.assertEqual(mail['attachments'][0].name, u'Eingangsbestätigung und Hinweis auf Unzustellbarkeit - Username.pdf')

    def test_attachment_name_redaction(self):
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        user = factories.UserFactory.create(last_name='Username')
        profile = user.get_profile()
        profile.private = True
        profile.save()
        request.user = user
        request.save()
        with open(p("test_mail_06.txt"), 'rb') as f:
            parser = EmailParser()
            content = f.read()
            mail = parser.parse(BytesIO(content))
            self.assertEqual(len(mail['attachments']), 1)
            self.assertEqual(mail['attachments'][0].name, u'Eingangsbestätigung und Hinweis auf Unzustellbarkeit - Username.pdf')
        request.add_message_from_email(mail, content)
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        mes = messages[1]
        self.assertEqual(mes.attachments[0].name, u'EingangsbesttigungundHinweisaufUnzustellbarkeit-NAME.pdf')

    def test_attachment_name_parsing(self):
        with open(p("test_mail_07.txt"), 'rb') as f:
            parser = EmailParser()
            content = f.read()
            mail = parser.parse(BytesIO(content))
            self.assertEqual(len(mail['attachments']), 1)
            self.assertEqual(mail['attachments'][0].name, u'Bescheid Fäker.pdf')

    def test_address_list(self):
        with open(p("test_mail_01.txt"), 'rb') as f:
            parser = EmailParser()
            content = f.read()
            mail = parser.parse(BytesIO(content))
            self.assertEqual(len(mail['cc']), 5)


class DeferredMessageTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()
        self.req = factories.FoiRequestFactory.create(site=self.site,
            secret_address="sw+yurpykc1hr@fragdenstaat.de")
        factories.FoiMessageFactory.create(request=self.req)

    def test_deferred(self):
        count_messages = len(self.req.messages)
        name, domain = self.req.secret_address.split('@')
        bad_mail = '@'.join((name + 'x', domain))
        with open(p("test_mail_01.txt"), 'rb') as f:
            mail = f.read().decode('ascii')
        mail = mail.replace(u'sw+yurpykc1hr@fragdenstaat.de', bad_mail)
        process_mail.delay(mail.encode('ascii'))
        self.assertEqual(count_messages,
            FoiMessage.objects.filter(request=self.req).count())
        dms = DeferredMessage.objects.filter(recipient=bad_mail)
        self.assertEqual(len(dms), 1)
        dm = dms[0]
        dm.redeliver(self.req)
        req = FoiRequest.objects.get(id=self.req.id)
        self.assertEqual(len(req.messages), count_messages + 1)
        dm = DeferredMessage.objects.get(id=dm.id)
        self.assertEqual(dm.request, req)


class PostMarkMailTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()
        date = datetime(2010, 6, 5, 5, 54, 40, tzinfo=timezone.utc)
        req = factories.FoiRequestFactory.create(site=self.site,
            secret_address="sw+yurpykc1hr@fragdenstaat.de",
            first_message=date, last_message=date)
        factories.FoiMessageFactory.create(request=req, timestamp=date)
        self.post_data = {
            "From": "myUser@example.com",
            "FromFull": {
                "Email": "myUser@example.com",
                "Name": "John Doe"
            },
            "To": "sw+yurpykc1hr@fragdenstaat.de",
            "ToFull": [
                {
                    "Email": "sw+yurpykc1hr@fragdenstaat.de",
                    "Name": ""
                }
            ],
            "Cc": "\"Full name\" <sample.cc@example.com>, \"Another Cc\" <another.cc@example.com>",
            "CcFull": [
                {
                    "Email": "sample.cc@example.com",
                    "Name": "Full name"
                },
                {
                    "Email": "another.cc@example.com",
                    "Name": "Another Cc"
                }
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
                    "Value": "SpamAssassin 3.3.1 (2010-03-16) onrs-ord-pm-inbound1.wildbit.com"
                },
                {
                    "Name": "X-Spam-Status",
                    "Value": "No"
                },
                {
                    "Name": "X-Spam-Score",
                    "Value": "-0.1"
                },
                {
                    "Name": "X-Spam-Tests",
                    "Value": "DKIM_SIGNED,DKIM_VALID,DKIM_VALID_AU,SPF_PASS"
                },
                {
                    "Name": "Received-SPF",
                    "Value": "Pass (sender SPF authorized) identity=mailfrom; client-ip=209.85.160.180; helo=mail-gy0-f180.google.com; envelope-from=myUser@theirDomain.com; receiver=451d9b70cf9364d23ff6f9d51d870251569e+ahoy@inbound.postmarkapp.com"
                },
                {
                    "Name": "DKIM-Signature",
                    "Value": "v=1; a=rsa-sha256; c=relaxed\/relaxed;                d=wildbit.com; s=google;                h=mime-version:reply-to:date:message-id:subject:from:to:cc                 :content-type;                bh=cYr\/+oQiklaYbBJOQU3CdAnyhCTuvemrU36WT7cPNt0=;                b=QsegXXbTbC4CMirl7A3VjDHyXbEsbCUTPL5vEHa7hNkkUTxXOK+dQA0JwgBHq5C+1u                 iuAJMz+SNBoTqEDqte2ckDvG2SeFR+Edip10p80TFGLp5RucaYvkwJTyuwsA7xd78NKT                 Q9ou6L1hgy\/MbKChnp2kxHOtYNOrrszY3JfQM="
                },
                {
                    "Name": "MIME-Version",
                    "Value": "1.0"
                },
                {
                    "Name": "Message-ID",
                    "Value": "<CAGXpo2WKfxHWZ5UFYCR3H_J9SNMG+5AXUovfEFL6DjWBJSyZaA@mail.example.com>"
                }
            ],
            "Attachments": [
                {
                    "Name": "myimage.png",
                    "Content": "[BASE64-ENCODED CONTENT]",
                    "ContentType": "image/png",
                    "ContentLength": 4096,
                    "ContentID": "myimage.png@01CE7342.75E71F80"
                },
                {
                    "Name": "mypaper.doc",
                    "Content": "[BASE64-ENCODED CONTENT]",
                    "ContentType": "application/msword",
                    "ContentLength": 16384,
                    "ContentID": ""
                }
            ]
        }

    def test_postmark_post(self, url=None):
        if url is None:
            url = reverse('foirequest-postmark_inbound')
        response = self.client.post(
            url,
            json.dumps(self.post_data),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        mes = request.messages[-1]
        self.assertEqual(mes.sender_email, 'myUser@example.com')

    def test_postmark_bounce(self):
        self.test_postmark_post(url=reverse('foirequest-postmark_bounce'))
