# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission

from froide.publicbody.models import PublicBody
from froide.foirequest.tests import factories
from froide.foirequest.models import FoiProject, FoiRequest


User = get_user_model()


class RequestProjectTest(TestCase):

    def setUp(self):
        factories.make_world()
        self.pb1 = PublicBody.objects.filter(jurisdiction__slug='bund')[0]
        self.pb2 = PublicBody.objects.filter(jurisdiction__slug='nrw')[0]
        ct = ContentType.objects.get_for_model(FoiRequest)
        self.perm = Permission.objects.get(
            content_type=ct,
            codename='create_batch'
        )

    def test_create_project(self):
        user = User.objects.get(email='info@fragdenstaat.de')
        user.user_permissions.add(self.perm)

        ok = self.client.login(email=user.email, password='froide')
        self.assertTrue(ok)

        pb_ids = '%s+%s' % (self.pb1.pk, self.pb2.pk)
        response = self.client.get(reverse('foirequest-make_request',
                kwargs={'publicbody_ids': pb_ids}))
        self.assertEqual(response.status_code, 200)
        data = {
            "subject": "Test-Subject",
            "body": "This is another test body with Ümläut€n",
            'public': 'on',
            'publicbody': pb_ids.split('+')
        }
        mail.outbox = []
        response = self.client.post(reverse('foirequest-make_request'), data)
        self.assertEqual(response.status_code, 302)
        project = FoiProject.objects.get(title=data['subject'])
        self.assertEqual(set([str(x.pk) for x in project.publicbodies.all()]),
                         set(pb_ids.split('+')))
        request_sent = reverse('foirequest-request_sent') + '?project=%s' % project.pk
        self.assertEqual(response['Location'], request_sent)
        self.assertEqual(project.title, data['subject'])
        self.assertEqual(project.description, data['body'])
        self.assertEqual(project.foirequest_set.all().count(), 2)
        self.assertEqual(len(mail.outbox), 3)  # 2 to pb, one to user
        requests = project.foirequest_set.all()
        first_message_1 = requests[0].messages[0]
        first_message_2 = requests[1].messages[0]
        self.assertNotEqual(first_message_1.plaintext, data['body'])
        last_part_1 = first_message_1.plaintext.split(data['body'])[1]
        last_part_2 = first_message_2.plaintext.split(data['body'])[1]
        self.assertNotEqual(last_part_1, last_part_2)

        response = self.client.get(reverse('foirequest-project_shortlink',
                kwargs={"obj_id": project.pk}))
        self.assertEqual(response.status_code, 302)

    def test_create_project_full_text(self):
        user = User.objects.get(email='info@fragdenstaat.de')
        user.user_permissions.add(self.perm)

        ok = self.client.login(email=user.email, password='froide')
        self.assertTrue(ok)

        pb_ids = (self.pb1.pk, self.pb2.pk)
        data = {
            "subject": "Test-Subject",
            "body": "This is another test body with Ümläut€n",
            'public': 'on',
            'publicbody': pb_ids,
            'full_text': 'on'
        }
        response = self.client.post(reverse('foirequest-make_request'), data)
        self.assertEqual(response.status_code, 302)
        project = FoiProject.objects.get(title=data['subject'])
        requests = project.foirequest_set.all()
        first_message_1 = requests[0].messages[0]
        first_message_2 = requests[1].messages[0]
        self.assertTrue(first_message_1.plaintext.startswith(data['body']))
        self.assertTrue(first_message_2.plaintext.startswith(data['body']))
