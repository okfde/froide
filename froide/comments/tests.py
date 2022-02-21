from unittest.mock import patch

from django.apps import apps
from django.test import TestCase

from .apps import CommentConfig, cancel_user, merge_user


class CommentConfigTest(TestCase):

    # Check if class parameters exist and have correct type
    def test_constructor(self):
        comment_config = apps.get_app_config("comments")
        self.assertIsInstance(comment_config, CommentConfig)
        self.assertEqual(comment_config.name, "froide.comments")
        self.assertEqual(comment_config.verbose_name, "Comments")

    # Check if signals are called once with correct parameters
    def test_ready(self):
        comment_config = apps.get_app_config("comments")
        with patch(
            "froide.account.account_canceled.connect"
        ) as account_canceled_connect, patch(
            "froide.account.account_merged.connect"
        ) as account_merged_connect:
            comment_config.ready()
            account_canceled_connect.assert_called_once_with(cancel_user)
            account_merged_connect.assert_called_once_with(merge_user)
