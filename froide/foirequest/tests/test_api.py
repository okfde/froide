from __future__ import with_statement

from django.test import TestCase

from froide.foirequest.tests import factories
from froide.foirequest.models import FoiRequest, FoiAttachment


class ApiTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_list(self):
        response = self.client.get('/api/v1/request/?format=json')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/api/v1/message/?format=json')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/api/v1/attachment/?format=json')
        self.assertEqual(response.status_code, 200)

    def test_detail(self):
        req = FoiRequest.objects.all()[0]
        response = self.client.get('/api/v1/request/%d/?format=json' % req.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn(req.title, response.content)
        self.assertNotIn(req.secret_address, response.content)
        prof = req.user.get_profile()
        prof.private = True
        prof.save()

        mes = factories.FoiMessageFactory.create(
            request=req,
            subject=req.user.get_full_name(),
            plaintext=u'Hallo %s,\n%s\n%s' % (
                req.user.get_full_name(),
                req.secret_address,
                prof.address
            )
        )
        response = self.client.get('/api/v1/message/%d/?format=json' % mes.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(req.user.get_full_name(), response.content)
        self.assertNotIn(req.secret_address, response.content)
        self.assertNotIn(prof.address, response.content)

        att = FoiAttachment.objects.all()[0]
        att.approved = True
        att.save()
        response = self.client.get('/api/v1/attachment/%d/?format=json' % att.pk)
        self.assertEqual(response.status_code, 200)

    def test_permissions(self):
        req = factories.FoiRequestFactory.create(
            visibility=1, site=self.site)

        response = self.client.get('/api/v1/request/%d/?format=json' % req.pk)
        self.assertEqual(response.status_code, 404)

        mes = factories.FoiMessageFactory.create(request=req)
        response = self.client.get('/api/v1/message/%d/?format=json' % mes.pk)
        self.assertEqual(response.status_code, 404)

        att = factories.FoiAttachmentFactory.create(belongs_to=mes)
        att.approved = True
        att.save()
        response = self.client.get('/api/v1/attachment/%d/?format=json' % att.pk)
        self.assertEqual(response.status_code, 404)

    def test_content_hidden(self):
        marker = u'TESTMARKER'
        mes = factories.FoiMessageFactory.create(
            content_hidden=True,
            plaintext=marker
        )
        response = self.client.get('/api/v1/message/%d/?format=json' % mes.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(marker, response.content)

    def test_username_hidden(self):
        user = factories.UserFactory.create(
            first_name='Reinhardt'
        )
        profile = user.get_profile()
        profile.private = True
        profile.save()
        mes = factories.FoiMessageFactory.create(
            content_hidden=True,
            sender_user=user
        )
        response = self.client.get('/api/v1/message/%d/?format=json' % mes.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(user.username, response.content)
        self.assertNotIn(user.first_name, response.content)

    def test_search(self):
        response = self.client.get('/api/v1/request/search/?format=json&q=Number')
        self.assertEqual(response.status_code, 200)
