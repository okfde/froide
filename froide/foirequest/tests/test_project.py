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
        print(response['Location'])
        self.assertIn(project.get_absolute_url(), response['Location'])
        self.assertEqual(project.title, data['subject'])
        self.assertEqual(project.description, data['body'])
        self.assertEqual(project.foirequest_set.all().count(), 2)
        self.assertEqual(len(mail.outbox), 3)  # 2 to pb, one to user
