# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta
import re

from django.test import TestCase
from django.test.utils import override_settings
from django.template import engines

from .text_utils import replace_email_name, remove_closing
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

        removed = remove_closing(closings, content)
        self.assertNotIn('Peter Parker', removed)


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


class TestThemeLoader(TestCase):

    @override_settings(FROIDE_THEME='froide.foirequest')
    def test_loader(self):
        from .theme_utils import ThemeLoader

        tl = ThemeLoader(engines['django'])
        sources = list(tl.get_template_sources('index.html'))
        self.assertEqual(len(sources), 1)
        origin = sources[0]
        self.assertTrue(origin.name.startswith('/'))
        self.assertTrue(origin.name.endswith('froide/foirequest/templates/index.html'))
