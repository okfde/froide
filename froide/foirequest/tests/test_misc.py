from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from django.utils.safestring import SafeString

import pytest

from froide.comments.models import FroideComment
from froide.foirequest.models import FoiMessage, FoiRequest
from froide.foirequest.notifications import (
    Notification,
    batch_update_requester,
    send_update,
)
from froide.foirequest.tasks import (
    classification_reminder,
    detect_asleep,
    detect_overdue,
)
from froide.foirequest.templatetags.foirequest_tags import (
    check_same_request,
    render_message_content,
)
from froide.foirequest.tests import factories
from froide.foirequest.utils import MailAttachmentSizeChecker


class TemplateTagTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_check_same_request(self):
        user_1 = factories.UserFactory.create()
        user_2 = factories.UserFactory.create()
        user_3 = factories.UserFactory.create()
        original = factories.FoiRequestFactory.create(user=user_1, site=self.site)
        same_1 = factories.FoiRequestFactory.create(
            user=user_2, same_as=original, site=self.site
        )
        same_2 = factories.FoiRequestFactory.create(
            user=user_3, same_as=original, site=self.site
        )

        result = check_same_request(original, user_2)
        self.assertEqual(result, same_1)

        result = check_same_request(same_2, user_2)
        self.assertEqual(result, same_1)

        result = check_same_request(same_2, user_1)
        self.assertEqual(result, False)


class TaskTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_detect_asleep(self):
        fr = FoiRequest.objects.all()[0]
        fr.last_message = fr.last_message - timedelta(days=31 * 6)
        fr.status = FoiRequest.STATUS.AWAITING_RESPONSE
        fr.save()
        mail.outbox = []
        detect_asleep.delay()
        fr = FoiRequest.objects.get(pk=fr.pk)
        self.assertEqual(fr.status, FoiRequest.STATUS.ASLEEP)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Request became asleep", mail.outbox[0].subject)

    def test_detect_overdue(self):
        fr = FoiRequest.objects.all()[0]
        fr.due_date = timezone.now() - timedelta(hours=5)
        fr.status = FoiRequest.STATUS.AWAITING_RESPONSE
        fr.save()
        self.assertEqual(fr.readable_status, "Response overdue")
        message_form = fr.get_send_message_form()
        self.assertIn("1 day late", message_form["message"].value())
        self.assertIn("#%d" % fr.pk, message_form["message"].value())
        mail.outbox = []
        detect_overdue.delay()
        fr = FoiRequest.objects.get(pk=fr.pk)
        self.assertEqual(fr.status, FoiRequest.STATUS.AWAITING_RESPONSE)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Request became overdue", mail.outbox[0].subject)

    def test_classification_reminder(self):
        fr = FoiRequest.objects.all()[0]
        fr.last_message = timezone.now() - timedelta(days=5)
        fr.status = FoiRequest.STATUS.AWAITING_CLASSIFICATION
        fr.save()
        mail.outbox = []
        classification_reminder.delay()
        fr = FoiRequest.objects.get(pk=fr.pk)
        self.assertEqual(fr.status, FoiRequest.STATUS.AWAITING_CLASSIFICATION)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(
            "Please classify the reply to your request", mail.outbox[0].subject
        )

    def test_requester_batch_update(self):
        fr = FoiRequest.objects.all()[0]

        end = timezone.now()
        start = end - timedelta(minutes=5)

        mail.outbox = []
        batch_update_requester(start=start, end=end)
        self.assertEqual(len(mail.outbox), 0)

        message = fr.messages[0]
        FroideComment.objects.create(
            content_type=ContentType.objects.get_for_model(FoiMessage),
            object_pk=message.id,
            user_name="Joe Somebody",
            comment="First!",
            submit_date=timezone.now() - timedelta(minutes=2),
            site=Site.objects.get_current(),
        )
        batch_update_requester(start=start, end=end)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Update on one of your request", mail.outbox[0].subject)


class SendUpdateTest(TestCase):
    def setUp(self):
        self.user1 = factories.UserFactory.create()
        self.user2 = factories.UserFactory.create()
        self.user3 = factories.UserFactory.create()

        # Some requests, all created by user 1.
        self.request1a = self.get_request(self.user1)
        self.request1b = self.get_request(self.user1)
        self.request1c = self.get_request(self.user1)

        # Notifications for comments by user X on request Y.
        self.comment_request1a_user1 = self.get_notification(
            self.request1a, self.user1, "Comment 1"
        )
        self.comment_request1a_user2 = self.get_notification(
            self.request1a, self.user2, "Comment 2"
        )
        self.comment_request1b_user2 = self.get_notification(
            self.request1b, self.user2, "Comment 3"
        )
        self.comment_request1c_user3 = self.get_notification(
            self.request1c, self.user3, "Comment 4"
        )
        self.comment_request1c_user2 = self.get_notification(
            self.request1c, self.user2, "Comment 5"
        )

        # Path to the send function to be patched.
        self.send_path = "froide.foirequest.notifications.update_requester_email.send"

    def get_request(self, user):
        request = factories.FoiRequestFactory.create()
        request.user = user
        return request

    def get_notification(self, request, user, event_name):
        notification = MagicMock(spec=Notification)
        notification.object = request
        notification.user_id = user.id
        notification.event = self.get_event(event_name)
        return notification

    def get_event(self, event_name):
        event = MagicMock()
        event.as_text.return_value = event_name
        return event

    def test_does_not_send_email_if_no_notifications(self):
        notifications = []

        with patch(self.send_path) as mock_send:
            send_update(notifications, self.user1)
            mock_send.assert_not_called()

    def test_does_not_include_requests_with_only_requester_comments(self):
        notifications = [self.comment_request1a_user1]

        with patch(self.send_path) as mock_send:
            send_update(notifications, self.user1)
            mock_send.assert_not_called()

    def test_includes_requests_with_only_non_requester_comments(self):
        notifications = [self.comment_request1a_user2]

        with patch(self.send_path) as mock_send:
            send_update(notifications, self.user1)
            mock_send.assert_called_once()

            context = mock_send.call_args[1]["context"]
            request_list = context["request_list"]

            assert context["user"] == self.user1
            assert context["count"] == 1
            assert len(request_list) == 1
            assert request_list[0]["request"] == self.request1a
            assert request_list[0]["events"] == ["Comment 2"]
            assert mock_send.call_args[1]["subject"] == "Update on one of your request"

    def test_includes_requests_with_both_requester_and_non_requester_comments(self):
        notifications = [self.comment_request1a_user1, self.comment_request1a_user2]

        with patch(self.send_path) as mock_send:
            send_update(notifications, self.user1)
            mock_send.assert_called_once()

            context = mock_send.call_args[1]["context"]
            request_list = context["request_list"]

            assert context["user"] == self.user1
            assert context["count"] == 1
            assert len(request_list) == 1
            assert request_list[0]["request"] == self.request1a
            assert request_list[0]["events"] == ["Comment 1", "Comment 2"]
            assert mock_send.call_args[1]["subject"] == "Update on one of your request"

    def test_includes_multiple_requests_with_comments_from_multiple_users(self):
        notifications = [
            self.comment_request1b_user2,
            self.comment_request1c_user3,
            self.comment_request1c_user2,
        ]

        with patch(self.send_path) as mock_send:
            send_update(notifications, self.user1)
            mock_send.assert_called_once()

            context = mock_send.call_args[1]["context"]
            request_list = context["request_list"]

            assert context["user"] == self.user1
            assert context["count"] == 2
            assert len(request_list) == 2
            assert request_list[0]["request"] == self.request1b
            assert request_list[0]["events"] == ["Comment 3"]
            assert request_list[1]["request"] == self.request1c
            assert request_list[1]["events"] == ["Comment 4", "Comment 5"]
            assert mock_send.call_args[1]["subject"] == "Update on 2 of your requests"


class MailAttachmentSizeCheckerTest(TestCase):
    def test_attachment_size_checker(self):
        files = [
            ("test1.txt", b"0" * 10, "text/plain"),
            ("test2.txt", b"0" * 10, "text/plain"),
            ("test3.txt", b"0" * 10, "text/plain"),
        ]
        checker = MailAttachmentSizeChecker(files, max_size=25)
        atts = list(checker)
        self.assertEqual(len(atts), 2)
        self.assertEqual(atts, files[:2])
        self.assertEqual(checker.send_files, ["test1.txt", "test2.txt"])
        self.assertEqual(checker.non_send_files, ["test3.txt"])


class RenderMessageContentTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()
        self.req = factories.FoiRequestFactory.create(site=self.site)

    def test_escapes_script_tag(self):
        plaintext = "<script>XSS</script>"
        expected = "&lt;script&gt;XSS&lt;/script&gt;"

        msg = factories.FoiMessageFactory.create(
            request=self.req, plaintext=plaintext, plaintext_redacted=plaintext
        )
        self.assertEqual(render_message_content(msg), expected)

    def test_escapes_a_tag(self):
        plaintext = '<a href="https://example.com">test</a>'
        expected = '&lt;a href="<a href="https://example.com" rel="nofollow" class="urlized" >https://example.com</a>"&gt;test&lt;/a&gt;'

        msg = factories.FoiMessageFactory.create(
            request=self.req, plaintext=plaintext, plaintext_redacted=plaintext
        )
        self.assertHTMLEqual(render_message_content(msg), expected)

    def test_no_mail(self):
        """
        This test is a regression test for https://github.com/okfde/froide/issues/508
        It was reported that sometimes quotes were double-escaped. This happened
        when the quote was in a string that looked like an email adress.
        """
        plaintext = """
        '@ with spaces'
        "@ with spaces"
        '@NoSpaces'
        "@NoSpaces"
        '@No.spacesAndDot'
        "@No.spacesAndDot"
        """
        expected = """
        &#x27;@ with spaces&#x27;
        &quot;@ with spaces&quot;
        &#x27;@NoSpaces&#x27;
        &quot;@NoSpaces&quot;
        &#x27;@No.spacesAndDot&#x27;
        &quot;@No.spacesAndDot&quot;
        """

        msg = factories.FoiMessageFactory.create(
            request=self.req, plaintext=plaintext, plaintext_redacted=plaintext
        )
        actual = render_message_content(msg)
        self.assertIsInstance(actual, SafeString)
        self.assertEqual(actual, expected)

    def test_redaction(self):
        expected = '<span class="redacted">[redacted]</span>'

        msg = factories.FoiMessageFactory.create(
            request=self.req, plaintext="aaaaa", plaintext_redacted="[redacted]"
        )
        self.assertEqual(render_message_content(msg), expected)


@pytest.mark.django_db
@pytest.mark.parametrize("auth", [True, False])
def test_redacted_content_cache(foi_message_factory, django_assert_num_queries, auth):
    redacted_foi_message = foi_message_factory(
        plaintext="Dear Mx. Example,\n\nPlease send me the following documents:\n\nGreetings,\nAlex Example",
        plaintext_redacted="Dear <<Redacted>>,\n\nPlease send me the following documents:\n\nGreetings,\n<<Redacted>>",
    )
    expected_redacted_content = {
        True: [
            [False, "Dear "],
            [True, "Mx. Example"],
            [False, ",\n\nPlease send me the following documents:\n\nGreetings,\n"],
            [True, "Alex Example"],
        ],
        False: [
            [False, "Dear "],
            [True, "<<Redacted>>"],
            [False, ",\n\nPlease send me the following documents:\n\nGreetings,\n"],
            [True, "<<Redacted>>"],
        ],
    }

    with django_assert_num_queries(1):
        redacted_content = redacted_foi_message.get_redacted_content(auth=auth)
        assert redacted_content == expected_redacted_content[auth]

    redacted_foi_message = FoiMessage.objects.get(id=redacted_foi_message.id)
    with django_assert_num_queries(0):
        redacted_content = redacted_foi_message.get_redacted_content(auth=auth)
        assert redacted_content == expected_redacted_content[auth]


@pytest.mark.django_db
@pytest.mark.parametrize("auth", [True, False])
def test_cached_rendered_content(
    foi_message_factory, django_assert_num_queries, auth, faker
):
    req_text = faker.text(max_nb_chars=FoiMessage.CONTENT_CACHE_THRESHOLD)
    redacted_foi_message = foi_message_factory(
        plaintext=f"Dear Mx. Example,\n\nPlease send me the following documents:\n{req_text}\n\nGreetings,\nAlex Example",
        plaintext_redacted=f"Dear <<Redacted>>,\n\nPlease send me the following documents:\n{req_text}\n\nGreetings,\n<<Redacted>>",
    )
    expected_redacted_content = {
        True: (
            'Dear <span class="redacted-dummy redacted-hover" data-bs-toggle="tooltip" title="Only '
            'visible to you">Mx. Example</span>,\n\nPlease send me the following documents:\n'
            f'{req_text}\n\nGreetings,\n<span class="redacted-dummy redacted-hover" data-bs-toggle='
            '"tooltip" title="Only visible to you">Alex Example</span>'
        ),
        False: (
            'Dear <span class="redacted">&lt;&lt;Redacted&gt;&gt;</span>,\n\nPlease send me the fol'
            f'lowing documents:\n{req_text}\n\nGreetings,\n<span class="redacted">&lt;&lt;Redacted&'
            "gt;&gt;</span>"
        ),
    }

    with django_assert_num_queries(1):
        redacted_content = render_message_content(redacted_foi_message, auth)
        assert redacted_content == expected_redacted_content[auth]

    redacted_foi_message = FoiMessage.objects.get(id=redacted_foi_message.id)
    with django_assert_num_queries(0):
        redacted_content = render_message_content(redacted_foi_message, auth)
        assert redacted_content == expected_redacted_content[auth]
        assert redacted_content == expected_redacted_content[auth]
