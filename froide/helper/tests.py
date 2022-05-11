import re
from datetime import datetime, timedelta
from re import Pattern

from django.test import TestCase
from django.test.utils import override_settings

from .csv_utils import dict_to_csv_stream
from .date_utils import calc_easter, calculate_month_range_de
from .email_sending import mail_registry
from .storage import make_unique_filename
from .text_diff import mark_differences
from .text_utils import remove_closing, replace_email_name, split_text_by_separator


def rec(x: str) -> Pattern:
    return re.compile(x, re.I | re.U)


class TestTextReplacement(TestCase):
    def test_email_name_replacement(self) -> None:
        content = "This is a very long string with a name <and.email@adress.in> it"
        content = replace_email_name(content, "REPLACEMENT")
        self.assertEqual(
            content, "This is a very long string with a name REPLACEMENT it"
        )

    def test_remove_closing(self) -> None:
        content = """
Sehr geehrte Frau Müller,

Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

Mit freundlichem Gruß

Peter Parker

More stuff here
        """

        closings = [
            rec("[Mm]it( den)? (freundliche(n|m)|vielen|besten) Gr(ü|u)(ß|ss)(en)?,?"),
            rec(r"Hochachtungsvoll,?"),
            rec(r"i\. ?A\."),
            rec(r"[iI]m Auftrag"),
        ]

        removed = remove_closing(content, closings)
        self.assertNotIn("Peter Parker", removed)

    def test_redactions_simple(self) -> None:
        original = """Ich bin am 21.10.2014 wieder an meinem Arbeitsplatz erreichbar. Ihre E-Mail wird nicht weitergeleitet. In dringenden Fällen wenden Sie sich bitte an amtsleitung-jobcenter@kreis-warendorf.de

Mit freundlichen Grüßen

Peter Parker
"""
        redacted = """Ich bin am 21.10.2014 wieder an meinem Arbeitsplatz erreichbar. Ihre E-Mail wird nicht weitergeleitet. In dringenden Fällen wenden Sie sich bitte an <<E-Mail-Adresse>>

Mit freundlichen Grüßen"""

        differences = mark_differences(original, redacted)
        self.assertEqual(2, differences.count("</span>"))

    def test_email_redaction(self) -> None:
        content = """Sehr geehrte(r) Anfragende(r),

die E-Mailadresse, an die Sie sich wenden können, lautet informationsfreiheitsgesetz@example.com. Hier werden Ihre Anfragen unmittelbar bearbeitet.

Eine inhaltliche Prüfung Ihrer Anfrage werden wir erst vornehmen, wenn Sie Ihre Identität mitteilen. Von einem Anfragenden kann erwartet werden, dass er/sie ein ernsthaftes Begehren vorbringt und zu seinem/ihrem Anliegen steht. Zudem kann ein Verwaltungsverfahren nicht aus dem Verborgenen heraus geführt werden.

Sollten Sie kein Interesse an der Veröffentlichung Ihres Namens auf der Website von FragDenStaat haben, können Sie uns auch gern direkt eine E-Mail zukommen lassen.

Vielen Dank für Ihr Verständnis.

Mit freundlichen Grüßen"""

        redacted = """Sehr geehrte(r) Anfragende(r),

die E-Mailadresse, an die Sie sich wenden können, lautet <<E-Mail-Adresse>>. Hier werden Ihre Anfragen unmittelbar bearbeitet.

Eine inhaltliche Prüfung Ihrer Anfrage werden wir erst vornehmen, wenn Sie Ihre Identität mitteilen. Von einem Anfragenden kann erwartet werden, dass er/sie ein ernsthaftes Begehren vorbringt und zu seinem/ihrem Anliegen steht. Zudem kann ein Verwaltungsverfahren nicht aus dem Verborgenen heraus geführt werden.

Sollten Sie kein Interesse an der Veröffentlichung Ihres Namens auf der Website von FragDenStaat haben, können Sie uns auch gern direkt eine E-Mail zukommen lassen.

Vielen Dank für Ihr Verständnis.

Mit freundlichen Grüßen"""
        res = mark_differences(content, redacted, attrs='class="redacted"')
        fake_res = content.replace(
            "informationsfreiheitsgesetz@example.com.",
            '<span class="redacted">informationsfreiheitsgesetz@example.com.</span>',
        )
        self.assertEqual(fake_res, res)


class TestTextSplitting(TestCase):
    def test_no_text_split(self) -> None:
        content = ""
        a, b = split_text_by_separator(content)
        self.assertEqual(a, "")
        self.assertEqual(b, "")

    def test_no_split(self) -> None:
        content = "content\ncontent"
        a, b = split_text_by_separator(content)
        self.assertEqual(a, content)
        self.assertEqual(b, "")

    def test_normal_text_split(self) -> None:
        content = "content\n\n---- forward ----\nother"
        a, b = split_text_by_separator(content)
        self.assertEqual(a, "content\n\n")
        self.assertEqual(b, "---- forward ----\nother")

    def test_notop_text_split(self) -> None:
        content = "---- top ----\ncontent\n\n---- middle ----\nbottom"
        a, b = split_text_by_separator(content)
        self.assertEqual(a, "---- top ----\ncontent\n\n")
        self.assertEqual(b, "---- middle ----\nbottom")


@override_settings(
    HOLIDAYS=[
        (1, 1),  # New Year's Day
        (5, 1),  # Labour Day
        (10, 3),  # Day of German reunification
        (12, 25),  # Christmas
        (12, 26),  # Second day of Christmas
    ],
    HOLIDAYS_WEEKENDS=True,
    HOLIDAYS_FOR_EASTER=(0, -2, 1, 39, 50, 60),
)
class TestGermanDeadline(TestCase):
    def test_german_holidays_send(self) -> None:
        easter_sunday = calc_easter(2014)
        easter_sunday = datetime(*easter_sunday)

        thursday = easter_sunday - timedelta(days=3) + timedelta(hours=15)
        self.assertEqual(thursday.hour, 15)
        thursday_night = easter_sunday - timedelta(days=3) + timedelta(hours=23)

        deadline = calculate_month_range_de(thursday)

        deadline2 = calculate_month_range_de(thursday_night)
        self.assertTrue(deadline2 > deadline)
        self.assertEqual((deadline + timedelta(days=4)).date(), deadline2.date())

    def test_german_holidays_receive(self) -> None:
        easter_sunday = calc_easter(2014)
        easter_sunday = datetime(*easter_sunday)

        month_before = easter_sunday - timedelta(days=33) + timedelta(hours=15)
        deadline = calculate_month_range_de(month_before)
        deadline = deadline.replace(tzinfo=None)
        self.assertTrue((deadline - month_before).days > 33)

    def test_long_period(self) -> None:
        start = datetime(2014, 10, 30)
        deadline = calculate_month_range_de(start, months=15)
        deadline = deadline.replace(tzinfo=None)
        self.assertEqual(deadline, datetime(2016, 2, 2))

    def test_last_day(self) -> None:
        start = datetime(2014, 1, 30)
        deadline = calculate_month_range_de(start, months=1)
        deadline = deadline.replace(tzinfo=None)
        self.assertEqual(deadline, datetime(2014, 3, 1))

    def test_end_of_year(self) -> None:
        start = datetime(2014, 11, 10)
        deadline = calculate_month_range_de(start, months=1)
        deadline = deadline.replace(tzinfo=None)
        self.assertEqual(deadline, datetime(2014, 12, 12))


class TestMailIntent(TestCase):
    def test_mail_intent_templates(self) -> None:
        for intent_key in mail_registry.intents:
            # check if all mail intent templates are present
            try:
                mail_registry.intents[intent_key].get_templates(needs_subject=False)
            except Exception:
                print("intent_key", intent_key)
                raise


class TestCSVFormulaEscape(TestCase):
    def test_formula_escape(self) -> None:
        data = [
            {
                "col1": "=SUM(1+1)",
                "col2": "+AVG(A2:A)",
                "col3": "-SUM(1+1)",
                "col4": '@SUM(1+1)+"X"',
            }
        ]
        csv_bytes = list(dict_to_csv_stream(data))

        self.assertEqual(csv_bytes[0].strip(), ",".join(data[0].keys()).encode("utf-8"))
        self.assertEqual(
            csv_bytes[1].strip(),
            b'\'=SUM(1+1),\'+AVG(A2:A),\'-SUM(1+1),"\'@SUM(1+1)+""X"""',
        )


class TestUniqueFilename(TestCase):
    def test_should_return_filename_when_it_does_not_exist_yet(self):
        filename = "test123.pdf"
        actual_new_filename = make_unique_filename(filename, [])

        self.assertEqual(actual_new_filename, filename)

    def test_should_return_filename_numbered_with_one_when_the_filename_already_exist(
        self,
    ):
        filename = "test123.pdf"

        actual_new_filename = make_unique_filename(filename, [filename])

        self.assertEqual(actual_new_filename, "test123_1.pdf")

    def test_filename_naming_scheme_incrementing(
        self,
    ):
        filename = "test123.pdf"
        filename_2 = "test123_1.pdf"

        actual_new_filename = make_unique_filename(filename, [filename, filename_2])

        self.assertEqual(actual_new_filename, "test123_2.pdf")
