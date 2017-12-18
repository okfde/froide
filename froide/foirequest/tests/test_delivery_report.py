# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from io import StringIO

import pytz

from django.test import TestCase
from django.utils.dateparse import parse_datetime
from django.conf import settings

from ..delivery import PostfixDeliveryReporter

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
