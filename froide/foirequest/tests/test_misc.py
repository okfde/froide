from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from froide.foirequest.models import FoiRequest
from froide.foirequest.tasks import (
    classification_reminder,
    detect_asleep,
    detect_overdue,
)
from froide.foirequest.templatetags.foirequest_tags import check_same_request
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
