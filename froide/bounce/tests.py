import os
import unittest
from datetime import datetime, timedelta

from django.test import TestCase
from django.db import connection

from froide.helper.email_utils import EmailParser
from froide.foirequest.tests.factories import UserFactory

from .models import Bounce
from .utils import (
    make_bounce_address, add_bounce_mail, check_user_deactivation,
    get_recipient_address_from_bounce
)


TEST_DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'testdata'))


def p(path):
    return os.path.join(TEST_DATA_ROOT, path)


@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific tests")
class BounceTest(TestCase):
    def setUp(self):
        self.email = 'nonexistant@example.org'

    def test_bounce_address(self):
        email = 'Upper_Case@example.org'
        bounce_address = make_bounce_address(email)
        self.assertEqual(bounce_address, bounce_address.lower())
        recovered_email, status = get_recipient_address_from_bounce(bounce_address)
        self.assertEqual(recovered_email, email.lower())
        self.assertTrue(status)

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

    def test_bounce_parsing_2(self):
        parser = EmailParser()
        with open(p("bounce_002.txt"), 'rb') as f:
            email = parser.parse(f)

        bounce_address = make_bounce_address(self.email)
        email.to = [('', bounce_address)]
        bounce_info = email.bounce_info
        self.assertTrue(bounce_info.is_bounce)
        self.assertEqual(bounce_info.bounce_type, 'hard')
        self.assertEqual(bounce_info.status, (5, 1, 1))

    def test_bounce_handling(self):
        def days_ago(days):
            return (datetime.now() - timedelta(days=days)).isoformat()

        def bounce_factory(days, bounce_type='hard'):
            return [{
                'is_bounce': True, 'bounce_type': bounce_type,
                'timestamp': days_ago(day)}
                for day in days
            ]

        bounce = Bounce(user=None, email='a@example.org',
                        bounces=bounce_factory([1, 5]))
        result = check_user_deactivation(bounce)
        self.assertIsNone(result)

        user = UserFactory()
        bounce = Bounce(user=user, email=user.email,
                        bounces=bounce_factory([1, 5]))
        result = check_user_deactivation(bounce)
        self.assertFalse(result)

        user = UserFactory()
        bounce = Bounce(user=user, email=user.email,
                        bounces=bounce_factory([1, 5, 12]))
        result = check_user_deactivation(bounce)
        self.assertTrue(result)

        user = UserFactory()
        bounce = Bounce(
            user=user, email=user.email,
            bounces=bounce_factory([1, 5, 12], bounce_type='soft'))
        result = check_user_deactivation(bounce)
        self.assertFalse(result)
