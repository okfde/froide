from datetime import timedelta

from django.test import TestCase
from django.core import mail
from django.utils import timezone

from froide.foirequest.tests import factories
from froide.foirequest.templatetags.foirequest_tags import check_same_request
from froide.foirequest.models import FoiRequest
from froide.foirequest.tasks import (detect_asleep, detect_overdue,
    classification_reminder)


class TemplateTagTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_check_same_request(self):
        context = {}
        var_name = 'same_as'
        user_1 = factories.UserFactory.create()
        user_2 = factories.UserFactory.create()
        user_3 = factories.UserFactory.create()
        original = factories.FoiRequestFactory.create(user=user_1,
                                                      site=self.site)
        same_1 = factories.FoiRequestFactory.create(user=user_2,
                                                    same_as=original,
                                                    site=self.site)
        same_2 = factories.FoiRequestFactory.create(user=user_3,
                                                    same_as=original,
                                                    site=self.site)

        check_same_request(context, original, user_2, var_name)
        self.assertEqual(context[var_name], same_1)

        check_same_request(context, same_2, user_2, var_name)
        self.assertEqual(context[var_name], same_1)

        check_same_request(context, same_2, user_1, var_name)
        self.assertEqual(context[var_name], False)


class TaskTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_detect_asleep(self):
        fr = FoiRequest.objects.all()[0]
        fr.last_message = fr.last_message - timedelta(days=31 * 6)
        fr.status = 'awaiting_response'
        fr.save()
        mail.outbox = []
        detect_asleep.delay()
        fr = FoiRequest.objects.get(pk=fr.pk)
        self.assertEqual(fr.status, 'asleep')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Request became asleep', mail.outbox[0].subject)

    def test_detect_overdue(self):
        fr = FoiRequest.objects.all()[0]
        fr.due_date = timezone.now() - timedelta(hours=5)
        fr.status = 'awaiting_response'
        fr.save()
        self.assertEqual(fr.readable_status, 'Response overdue')
        message_form = fr.get_send_message_form()
        self.assertIn('1 day late', message_form['message'].value())
        self.assertIn('#%d' % fr.pk, message_form['message'].value())
        mail.outbox = []
        detect_overdue.delay()
        fr = FoiRequest.objects.get(pk=fr.pk)
        self.assertEqual(fr.status, 'awaiting_response')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Request became overdue', mail.outbox[0].subject)

    def test_classification_reminder(self):
        fr = FoiRequest.objects.all()[0]
        fr.last_message = timezone.now() - timedelta(days=5)
        fr.status = 'awaiting_classification'
        fr.save()
        mail.outbox = []
        classification_reminder.delay()
        fr = FoiRequest.objects.get(pk=fr.pk)
        self.assertEqual(fr.status, 'awaiting_classification')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Please classify the reply to your request',
                      mail.outbox[0].subject)
