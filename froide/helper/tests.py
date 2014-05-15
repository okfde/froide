from datetime import datetime, timedelta

from django.test import TestCase
from django.test.utils import override_settings

from .text_utils import replace_email_name
from .form_generator import FormGenerator
from .date_utils import calc_easter, calculate_month_range_de


class TestAPIDocs(TestCase):
    def test_api_docs_main(self):
        response = self.client.get('/api/v1/docs/')
        self.assertEqual(response.status_code, 200)

    def test_api_docs_resource(self):
        response = self.client.get('/api/v1/docs/resources/')
        self.assertEqual(response.status_code, 200)


class TestTextReplacement(TestCase):
    def test_email_name_replacement(self):
        content = 'This is a very long string with a name <and.email@adress.in> it'
        content = replace_email_name(content, 'REPLACEMENT')
        self.assertEqual(content, 'This is a very long string with a name REPLACEMENT it')


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

        tl = ThemeLoader()
        sources = list(tl.get_template_sources('index.html'))
        self.assertEqual(len(sources), 1)
        self.assertTrue(sources[0].startswith('/'))
        self.assertTrue(sources[0].endswith('froide/foirequest/templates/index.html'))


class TestFormGenerator(TestCase):
    def test_render(self):
        s = '''I choose
    ( o ) ice cream
    (   ) waffles
with
    [ x ] chocolate sauce
    [ x ] caramel cream
    [   ] extra sugar
and I like it
    ( o ) baked
    (   ) cooked
.
Cheers!'''
        form = FormGenerator(s, {
            'fg_radio_1': 'ice cream',
            'fg_check_3': 'yeah',
            'fg_check_1': 'on',
            'fg_radio_2': 'baked'
        })
        self.assertEqual(form.render_html(), '''I choose <label for="fg_option_1">
<input type="radio" id="fg_option_1" checked="checked" name="fg_radio_1"
 value="ice cream"/> ice cream</label> <label for="fg_option_2">
<input type="radio" id="fg_option_2" name="fg_radio_1" value="waffles"/>
 waffles</label> with <label for="fg_check_1">
<input type="checkbox" id="fg_check_1" checked="checked" name="fg_check_1"
 value="chocolate sauce"/> chocolate sauce</label> <label for="fg_check_2">
<input type="checkbox" id="fg_check_2" checked="checked" name="fg_check_2"
 value="caramel cream"/> caramel cream</label> <label for="fg_check_3">
<input type="checkbox" id="fg_check_3" name="fg_check_3" value="extra sugar"/>
 extra sugar</label> and I like it <label for="fg_option_3">
<input type="radio" id="fg_option_3" checked="checked" name="fg_radio_2"
 value="baked"/> baked</label> <label for="fg_option_4">
<input type="radio" id="fg_option_4" name="fg_radio_2" value="cooked"/>
 cooked</label>.'''.replace('\n', '') + '\nCheers!''')
        self.assertEqual(form.render(), 'I choose ice cream with chocolate sauce extra sugar and I like it baked.\nCheers!')
