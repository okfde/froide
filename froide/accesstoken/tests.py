# import unittest
import uuid

from django.test import TestCase

from froide.foirequest.tests.factories import UserFactory

from .models import AccessTokenManager

# from .models import AccessToken


class AccessTokenManagerTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.purpose = "test_purpose"

    def test_create_for_user(self):
        at_manager = AccessTokenManager()
        accesstoken = at_manager.create_for_user(self.user, self.purpose)
        self.assertIsInstance(accesstoken, uuid.UUID)

    # def test_reset(self):

    # def test_get_token_by_user(self):

    # def test_get_by_user(self):

    # def test_get_by_token(self):

    # def test_get_user_by_token(self):


# class AccessTokenTest(TestCase):
# def setUp(self):
# self.token =
# self.purpose =
# self.user =
# self.timestamp =
