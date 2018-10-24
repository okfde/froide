import os

from django.test import TestCase

from froide.helper.email_utils import EmailParser

from .models import Bounce
from .utils import make_bounce_address, add_bounce_mail


TEST_DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'testdata'))


def p(path):
    return os.path.join(TEST_DATA_ROOT, path)


class MailTest(TestCase):
    def setUp(self):
        self.email = 'nonexistant@example.org'

    def test_bounce_parsing(self):
        parser = EmailParser()
        with open(p("bounce_001.txt"), 'rb') as f:
            email = parser.parse(f)

        bounce_address = make_bounce_address(self.email)
        email.to = [('', bounce_address)]
        bounce_info = email.bounce_info
        self.assertTrue(bounce_info.is_bounce)
        self.assertEqual(bounce_info.bounce_type, 'hard')
        self.assertEqual(bounce_info.status, (5, 0, 0))
        add_bounce_mail(email)
        bounce = Bounce.objects.get(email=self.email)
        self.assertEqual(bounce.email, self.email)
        self.assertIsNone(bounce.user)
        self.assertEqual(len(bounce.bounces), 1)
