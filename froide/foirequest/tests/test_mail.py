# -*- coding: utf-8 -*-
from __future__ import with_statement

import os
from datetime import datetime

from django.test import TestCase
from django.core import mail
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils import timezone

from froide.helper.email_utils import EmailParser

from froide.foirequest.tasks import _process_mail
from froide.foirequest.models import FoiRequest
from froide.foirequest.tests import factories

FILE_ROOT = os.path.abspath(os.path.dirname(__file__))


def p(path):
    return os.path.join(FILE_ROOT, path)


class MailTest(TestCase):
    def setUp(self):
        site = factories.make_world()
        req = factories.FoiRequestFactory.create(site=site,
            secret_address="sw+yurpykc1hr@fragdenstaat.de")
        factories.FoiMessageFactory.create(request=req)

    def test_working(self):
        with file(p("test_mail_01.txt")) as f:
            _process_mail(f.read())
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        self.assertIn(u'J\xf6rg Gahl-Killen', [m.sender_name for m in messages])
        message = messages[1]
        self.assertEqual(message.timestamp,
                datetime(2010, 7, 5, 5, 54, 40, tzinfo=timezone.utc))

    def test_working_with_attachment(self):
        with file(p("test_mail_02.txt")) as f:
            _process_mail(f.read())
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1].subject, u"Fwd: Informationsfreiheitsgesetz des Bundes, Antragsvordruck für Open Data")
        self.assertEqual(len(messages[1].attachments), 1)
        self.assertEqual(messages[1].attachments[0].name, u"TI-IFG-AntragVordruck.docx")

    def test_wrong_address(self):
        request = FoiRequest.objects.get_by_secret_mail(u"sw+yurpykc1hr@fragdenstaat.de")
        request.delete()
        mail.outbox = []
        with file(p("test_mail_01.txt")) as f:
            _process_mail(f.read())
        self.assertEqual(len(mail.outbox), len(settings.MANAGERS))
        self.assertTrue(all([_('Unknown FoI-Mail Recipient') in m.subject for m in mail.outbox]))
        recipients = [m.to[0] for m in mail.outbox]
        for manager in settings.MANAGERS:
            self.assertIn(manager[1], recipients)

    def test_inline_attachments(self):
        parser = EmailParser()
        with file(p("test_mail_03.txt")) as f:
            email = parser.parse(f.read())
        self.assertEqual(len(email['attachments']), 1)

    def test_long_attachment_names(self):
        req = FoiRequest.objects.all()[0]
        with file(p("test_mail_04.txt"), 'rb') as f:
            parser = EmailParser()
            content = f.read()
            mail = parser.parse(content)
        self.assertEqual(mail['subject'], u'Kooperationen des Ministerium für Schule und '
                u'Weiterbildung des Landes Nordrhein-Westfalen mit außerschulischen Partnern')
        self.assertEqual(mail['attachments'][0].name, u'Kooperationen des MSW, Antrag '
                'nach Informationsfreiheitsgesetz NRW, Stefan Safario vom 06.12.2012 - AW vom '
                '08.01.2013 - RS.pdf')
        req.add_message_from_email(mail, content)
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1].subject, mail['subject'])
        self.assertEqual(len(messages[1].attachments), 2)
        self.assertEqual(messages[1].attachments[0].name, u"KooperationendesMSWAntragnachInformationsfreiheitsgesetzNRWStefanSafariovom06.12.2012-AWvom08.01.2013-RS.pdf")
