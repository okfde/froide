import os
import unittest
from datetime import datetime, timedelta

from django.db import connection
from django.test import TestCase

from froide.foirequest.tests.factories import UserFactory
from froide.helper.email_parsing import parse_email

from .models import Bounce
from .utils import (
    add_bounce_mail,
    check_deactivation_condition,
    get_recipient_address_from_bounce,
    make_bounce_address,
)

TEST_DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "testdata"))


def p(path: str) -> str:
    return os.path.join(TEST_DATA_ROOT, path)


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
class BounceTest(TestCase):
    def setUp(self) -> None:
        self.email = "nonexistant@example.org"

    def test_bounce_address(self) -> None:
        email = "Upper_Case@example.org"
        bounce_address = make_bounce_address(email)
        self.assertEqual(bounce_address, bounce_address.lower())
        recovered_email, status = get_recipient_address_from_bounce(bounce_address)
        self.assertEqual(recovered_email, email.lower())
        self.assertTrue(status)

    def test_bounce_parsing(self) -> None:
        with open(p("bounce_001.txt"), "rb") as f:
            email = parse_email(f)

        bounce_address = make_bounce_address(self.email)
        email.to = [("", bounce_address)]
        bounce_info = email.bounce_info
        self.assertTrue(bounce_info.is_bounce)
        self.assertEqual(bounce_info.bounce_type, "hard")
        self.assertEqual(bounce_info.status, (5, 5, 3))
        add_bounce_mail(email)
        bounce = Bounce.objects.get(email=self.email)
        self.assertEqual(bounce.email, self.email)
        self.assertIsNone(bounce.user)
        self.assertEqual(len(bounce.bounces), 1)

    def test_bounce_parsing_2(self) -> None:
        with open(p("bounce_002.txt"), "rb") as f:
            email = parse_email(f)

        bounce_address = make_bounce_address(self.email)
        email.to = [("", bounce_address)]
        bounce_info = email.bounce_info
        self.assertTrue(bounce_info.is_bounce)
        self.assertEqual(bounce_info.bounce_type, "hard")
        self.assertEqual(bounce_info.status, (5, 1, 1))

    def test_bounce_handling(self) -> None:
        def days_ago(days):
            return (datetime.now() - timedelta(days=days)).isoformat()

        def bounce_factory(days, bounce_type="hard"):
            return [
                {
                    "is_bounce": True,
                    "bounce_type": bounce_type,
                    "timestamp": days_ago(day),
                }
                for day in days
            ]

        bounce = Bounce(
            user=None, email="a@example.org", bounces=bounce_factory([1, 5])
        )
        result = check_deactivation_condition(bounce)
        self.assertFalse(result)

        user = UserFactory()
        bounce = Bounce(user=user, email=user.email, bounces=bounce_factory([1, 5]))
        result = check_deactivation_condition(bounce)
        self.assertFalse(result)

        user = UserFactory()
        bounce = Bounce(user=user, email=user.email, bounces=bounce_factory([1, 5, 12]))
        result = check_deactivation_condition(bounce)
        self.assertTrue(result)

        user = UserFactory()
        bounce = Bounce(
            user=user,
            email=user.email,
            bounces=bounce_factory([1, 5, 12], bounce_type="soft"),
        )
        result = check_deactivation_condition(bounce)
        self.assertFalse(result)
