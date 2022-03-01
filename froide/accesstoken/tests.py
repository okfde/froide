import uuid
from datetime import datetime

from django.test import TestCase

from froide.account.models import User
from froide.foirequest.tests.factories import UserFactory

from .models import AccessToken, AccessTokenManager


class AccessTokenManagerTest(TestCase):
    def setUp(self):
        self.purpose = "test_purpose"
        self.at_manager = AccessTokenManager()

    # Check if accesstoken is created and of correct type
    def test_create_for_user(self):
        user = UserFactory()
        accesstoken = self.at_manager.create_for_user(user, self.purpose)
        self.assertIsInstance(accesstoken, uuid.UUID)

    # Check if accesstoken is actually changed on reset and of correct type
    def test_reset(self):
        user = UserFactory()
        old_token = self.at_manager.create_for_user(user, self.purpose)
        new_token = self.at_manager.reset(user, self.purpose)
        self.assertNotEqual(old_token, new_token)
        self.assertIsInstance(new_token, uuid.UUID)

    # Check if correct accesstoken is returned
    def test_get_token_by_user(self):
        user = UserFactory()
        accesstoken = self.at_manager.create_for_user(user, self.purpose)
        received_token = self.at_manager.get_token_by_user(user, self.purpose)
        self.assertEqual(accesstoken, received_token)

    # Check correct behaviour if accesstoken does not exist
    # Check correct return type
    def test_get_by_user(self):
        user = UserFactory()
        ret_value = self.at_manager.get_by_user(user, self.purpose)
        self.assertEqual(ret_value, None)
        self.at_manager.create_for_user(user, self.purpose)
        ret_value = self.at_manager.get_by_user(user, self.purpose)
        self.assertIsInstance(ret_value, AccessToken)

    # Check correct behaviour if user does not exist
    # Check correct return type
    def test_get_by_token(self):
        at = AccessToken()
        ret_value = self.at_manager.get_by_token(at.token, self.purpose)
        self.assertEqual(ret_value, None)
        user = UserFactory()
        accesstoken = self.at_manager.create_for_user(user, self.purpose)
        ret_value = self.at_manager.get_by_token(accesstoken, self.purpose)
        self.assertIsInstance(ret_value, AccessToken)

    # Check if correct user is returned
    def test_get_user_by_token(self):
        user = UserFactory()
        accesstoken = self.at_manager.create_for_user(user, self.purpose)
        received_user = self.at_manager.get_user_by_token(accesstoken, self.purpose)
        self.assertEqual(user, received_user)


class AccessTokenTest(TestCase):
    def setUp(self):
        self.purpose = "test_purpose"
        self.at_manager = AccessTokenManager()

    # Check if class parameters exist and have correct type
    def test_constructor(self):
        user = UserFactory()
        self.at_manager.create_for_user(user, self.purpose)
        accesstoken = self.at_manager.get_by_user(user, self.purpose)
        self.assertIsInstance(accesstoken.token, uuid.UUID)
        self.assertIsInstance(accesstoken.purpose, str)
        self.assertIsInstance(accesstoken.user, User)
        self.assertIsInstance(accesstoken.timestamp, datetime)
        self.assertIsNotNone(accesstoken.user)
        self.assertIsNotNone(accesstoken.purpose)
