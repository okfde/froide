# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from io import StringIO

import pytz
from mock import patch, Mock

from django.test import TestCase
from django.utils.dateparse import parse_datetime
from django.conf import settings

from ..delivery import PostfixDeliveryReporter, DeliveryReport
from . import factories

log_string = """
Dec 10 14:30:19 fragdenstaat postfix/smtpd[31492]: A3CD32E0C2C: client=localhost[127.0.0.1], sasl_method=PLAIN, sasl_username=foimail@fragdenstaat.de
Dec 10 14:30:19 fragdenstaat postfix/cleanup[3361]: A3CD32E0C2C: message-id=<20171211133019.12503.3873@fragdenstaat.de>
Dec 10 14:30:19 fragdenstaat opendkim[1488]: A3CD32E0C2C: DKIM-Signature field added (s=mail, d=fragdenstaat.de)
Dec 10 14:30:19 fragdenstaat postfix/qmgr[31484]: A3CD32E0C2C: from=<s.peter.xyz123@fragdenstaat.de>, size=2369, nrcpt=1 (queue active)
Dec 11 14:30:25 fragdenstaat postfix/smtp[3365]: A3CD32E0C2C: to=<bad.testing@staedteregion-aachen.de>, relay=mail10.regioit-aachen.de[91.102.136.170]:25, delay=6.1, delays=0.23/0.02/0.13/5.8, dsn=2.0.0, status=sent (250 2.0.0 from MTA(smtp:[91.102.136.170]:10025): 250 2.0.0 Ok: queued as A1949380043)
Dec 11 14:30:19 fragdenstaat postfix/smtpd[31492]: 93CD32E0C2D: client=localhost[127.0.0.1], sasl_method=PLAIN, sasl_username=foimail@fragdenstaat.de
Dec 11 14:30:19 fragdenstaat postfix/cleanup[3361]: 93CD32E0C2D: message-id=<20171211133019.12503.3873@fragdenstaat.de>
Dec 11 14:30:19 fragdenstaat opendkim[1488]: 93CD32E0C2D: DKIM-Signature field added (s=mail, d=fragdenstaat.de)
Dec 11 14:30:19 fragdenstaat postfix/qmgr[31484]: 93CD32E0C2D: from=<s.peter.xyz123@fragdenstaat.de>, size=2369, nrcpt=1 (queue active)
Dec 11 14:30:25 fragdenstaat postfix/smtp[3365]: 93CD32E0C2D: to=<test.testing@staedteregion-aachen.de>, relay=mail10.regioit-aachen.de[91.102.136.170]:25, delay=6.1, status=deferred
Dec 11 14:30:25 fragdenstaat postfix/smtp[3365]: 93CD32E0C2D: to=<test.testing@staedteregion-aachen.de>, relay=mail10.regioit-aachen.de[91.102.136.170]:25, delay=6.1, delays=0.23/0.02/0.13/5.8, dsn=2.0.0, status=sent (250 2.0.0 from MTA(smtp:[91.102.136.170]:10025): 250 2.0.0 Ok: queued as A1949380043)
Dec 11 14:30:25 fragdenstaat postfix/qmgr[31484]: 93CD32E0C2D: removed
"""


class PostfixDeliveryReportTest(TestCase):
    def setUp(self):
        factories.make_world()

    def test_parsing(self):
        sender = 's.peter.xyz123@fragdenstaat.de'
        recipient = 'test.testing@staedteregion-aachen.de'

        pdl = PostfixDeliveryReporter(time_zone=settings.TIME_ZONE)
        log_file = StringIO(log_string)
        naive = parse_datetime("2017-12-11 14:28:45")

        timestamp = pytz.timezone(settings.TIME_ZONE).localize(naive, is_dst=None)

        result = pdl.search_log(log_file, sender, recipient, timestamp)
        self.assertEqual(result.status, 'sent')
        self.assertEqual(result.message_id, '20171211133019.12503.3873@fragdenstaat.de')

    @patch('froide.foirequest.delivery.get_delivery_report',
           lambda a, b, c: DeliveryReport('loglines', None, 'sent', 'message-id'))
    def test_delivery_report_sent(self):
        mes = factories.FoiMessageFactory.create(is_response=False)
        mes.check_delivery_status()
        self.assertIsNotNone(mes.deliverystatus)
        ds = mes.get_delivery_status()
        self.assertEqual(ds.status, 'sent')
        self.assertEqual(mes.email_message_id, 'message-id')

    def test_delivery_report_unavailable(self):
        mock = Mock(return_value=None)
        mes = factories.FoiMessageFactory.create(is_response=False)
        with patch('froide.foirequest.delivery.get_delivery_report', mock):
            mes.check_delivery_status(count=0)

        self.assertEqual(mock.call_count, 7)
        self.assertIsNone(mes.get_delivery_status())

    def test_delivery_report_deferred(self):
        mock = Mock(return_value=DeliveryReport('loglines', None, 'deferred', 'message-id-2'))
        mes = factories.FoiMessageFactory.create(is_response=False)
        with patch('froide.foirequest.delivery.get_delivery_report', mock):
            mes.check_delivery_status(count=0)

        self.assertEqual(mock.call_count, 7)
        ds = mes.get_delivery_status()
        self.assertEqual(ds.status, 'deferred')
        self.assertEqual(mes.email_message_id, 'message-id-2')
