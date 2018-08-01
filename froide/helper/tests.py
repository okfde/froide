# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta
import re

from django.test import TestCase
from django.test.utils import override_settings

from .text_utils import replace_email_name, remove_closing
from .text_diff import mark_differences
from .date_utils import calc_easter, calculate_month_range_de


def rec(x):
    return re.compile(x, re.I | re.U)


class TestTextReplacement(TestCase):
    def test_email_name_replacement(self):
        content = 'This is a very long string with a name <and.email@adress.in> it'
        content = replace_email_name(content, 'REPLACEMENT')
        self.assertEqual(content, 'This is a very long string with a name REPLACEMENT it')

    def test_remove_closing(self):
        content = '''
Sehr geehrte Frau Müller,

Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

Mit freundlichem Gruß

Peter Parker

More stuff here
        '''

        closings = [
            rec('[Mm]it( den)? (freundliche(n|m)|vielen|besten) Gr(ü|u)(ß|ss)(en)?,?'),
            rec(r'Hochachtungsvoll,?'),
            rec(r'i\. ?A\.'), rec(r'[iI]m Auftrag')
        ]

        removed = remove_closing(content, closings)
        self.assertNotIn('Peter Parker', removed)

    def test_redactions_simple(self):
        original = '''Ich bin am 21.10.2014 wieder an meinem Arbeitsplatz erreichbar. Ihre E-Mail wird nicht weitergeleitet. In dringenden Fällen wenden Sie sich bitte an amtsleitung-jobcenter@kreis-warendorf.de

Mit freundlichen Grüßen

Peter Parker
'''
        redacted = '''Ich bin am 21.10.2014 wieder an meinem Arbeitsplatz erreichbar. Ihre E-Mail wird nicht weitergeleitet. In dringenden Fällen wenden Sie sich bitte an <<E-Mail-Adresse>>

Mit freundlichen Grüßen'''

        differences = mark_differences(original, redacted)
        self.assertEqual(2, differences.count('</span>'))

    def test_email_redaction(self):
        content = '''Sehr geehrte(r) Anfragende(r),

die E-Mailadresse, an die Sie sich wenden können, lautet informationsfreiheitsgesetz@example.com. Hier werden Ihre Anfragen unmittelbar bearbeitet.

Eine inhaltliche Prüfung Ihrer Anfrage werden wir erst vornehmen, wenn Sie Ihre Identität mitteilen. Von einem Anfragenden kann erwartet werden, dass er/sie ein ernsthaftes Begehren vorbringt und zu seinem/ihrem Anliegen steht. Zudem kann ein Verwaltungsverfahren nicht aus dem Verborgenen heraus geführt werden.

Sollten Sie kein Interesse an der Veröffentlichung Ihres Namens auf der Website von FragDenStaat haben, können Sie uns auch gern direkt eine E-Mail zukommen lassen.

Vielen Dank für Ihr Verständnis.

Mit freundlichen Grüßen'''

        redacted = '''Sehr geehrte(r) Anfragende(r),

die E-Mailadresse, an die Sie sich wenden können, lautet <<E-Mail-Adresse>>. Hier werden Ihre Anfragen unmittelbar bearbeitet.

Eine inhaltliche Prüfung Ihrer Anfrage werden wir erst vornehmen, wenn Sie Ihre Identität mitteilen. Von einem Anfragenden kann erwartet werden, dass er/sie ein ernsthaftes Begehren vorbringt und zu seinem/ihrem Anliegen steht. Zudem kann ein Verwaltungsverfahren nicht aus dem Verborgenen heraus geführt werden.

Sollten Sie kein Interesse an der Veröffentlichung Ihres Namens auf der Website von FragDenStaat haben, können Sie uns auch gern direkt eine E-Mail zukommen lassen.

Vielen Dank für Ihr Verständnis.

Mit freundlichen Grüßen'''
        res = mark_differences(content, redacted)
        fake_res = content.replace('informationsfreiheitsgesetz@example.com', '<span class="redacted">informationsfreiheitsgesetz@example.com</span>')
        self.assertEqual(fake_res, res)


@override_settings(
    HOLIDAYS=[
        (1, 1),  # New Year's Day
        (5, 1),  # Labour Day
        (10, 3),  # Day of German reunification
        (12, 25),  # Christmas
        (12, 26),  # Second day of Christmas
    ],
    HOLIDAYS_WEEKENDS=True,
    HOLIDAYS_FOR_EASTER=(0, -2, 1, 39, 50, 60))
class TestGermanDeadline(TestCase):
    def test_german_holidays_send(self):
        easter_sunday = calc_easter(2014)
        easter_sunday = datetime(*easter_sunday)

        thursday = easter_sunday - timedelta(days=3) + timedelta(hours=15)
        self.assertEqual(thursday.hour, 15)
        thursday_night = easter_sunday - timedelta(days=3) + timedelta(hours=23)

        deadline = calculate_month_range_de(thursday)

        deadline2 = calculate_month_range_de(thursday_night)
        self.assertTrue(deadline2 > deadline)
        self.assertEqual((deadline + timedelta(days=4)).date(), deadline2.date())

    def test_german_holidays_receive(self):
        easter_sunday = calc_easter(2014)
        easter_sunday = datetime(*easter_sunday)

        month_before = easter_sunday - timedelta(days=33) + timedelta(hours=15)
        deadline = calculate_month_range_de(month_before)
        deadline = deadline.replace(tzinfo=None)
        self.assertTrue((deadline - month_before).days > 33)
