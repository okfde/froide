from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from froide.comments.models import FroideComment
from froide.foirequest.models import FoiMessage, FoiRequest
from froide.foirequest.notifications import batch_update_requester
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
        expected = '&lt;a href="<a href="https://example.com" rel="nofollow">https://example.com</a>"&gt;test&lt;/a&gt;'

        msg = factories.FoiMessageFactory.create(
            request=self.req, plaintext=plaintext, plaintext_redacted=plaintext
        )
        self.assertEqual(render_message_content(msg), expected)

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
        '@ with spaces'
        "@ with spaces"
        '@NoSpaces'
        "@NoSpaces"
        '@No.spacesAndDot'
        "@No.spacesAndDot"
        """

        msg = factories.FoiMessageFactory.create(
            request=self.req, plaintext=plaintext, plaintext_redacted=plaintext
        )
        self.assertEqual(render_message_content(msg), expected)

    def test_redaction(self):
        expected = '<span class="redacted">[redacted]</span>'

        msg = factories.FoiMessageFactory.create(
            request=self.req, plaintext="aaaaa", plaintext_redacted="[redacted]"
        )
        self.assertEqual(render_message_content(msg), expected)
