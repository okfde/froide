from __future__ import unicode_literals

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.test import TestCase

from froide.foirequest.tests import factories
from froide.foirequest.models import FoiRequest, FoiAttachment


class ApiTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_list(self):
        response = self.client.get('/api/v1/request/')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/api/v1/message/')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/api/v1/attachment/')
        self.assertEqual(response.status_code, 200)

    def test_detail(self):
        req = FoiRequest.objects.all()[0]
        response = self.client.get('/api/v1/request/%d/' % req.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, req.title)
        self.assertNotContains(response, req.secret_address)
        req.user.private = True
        req.user.save()

        mes = factories.FoiMessageFactory.create(
            request=req,
            subject=req.user.get_full_name(),
            plaintext='Hallo %s,\n%s\n%s' % (
                req.user.get_full_name(),
                req.secret_address,
                req.user.address
            )
        )
        response = self.client.get('/api/v1/message/%d/' % mes.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, req.user.get_full_name())
        self.assertNotContains(response, req.secret_address)
        self.assertNotContains(response, req.user.address)

        att = FoiAttachment.objects.all()[0]
        att.approved = True
        att.save()
        response = self.client.get('/api/v1/attachment/%d/' % att.pk)
        self.assertEqual(response.status_code, 200)

    def test_permissions(self):
        req = factories.FoiRequestFactory.create(
            visibility=FoiRequest.VISIBLE_TO_REQUESTER, site=self.site)

        response = self.client.get('/api/v1/request/%d/' % req.pk)
        self.assertEqual(response.status_code, 404)

        mes = factories.FoiMessageFactory.create(request=req)
        response = self.client.get('/api/v1/message/%d/' % mes.pk)
        self.assertEqual(response.status_code, 404)

        att = factories.FoiAttachmentFactory.create(belongs_to=mes)
        att.approved = True
        att.save()
        response = self.client.get('/api/v1/attachment/%d/' % att.pk)
        self.assertEqual(response.status_code, 404)

    def test_content_hidden(self):
        marker = 'TESTMARKER'
        mes = factories.FoiMessageFactory.create(
            content_hidden=True,
            plaintext=marker
        )
        response = self.client.get('/api/v1/message/%d/' % mes.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, marker)

    def test_username_hidden(self):
        user = factories.UserFactory.create(
            first_name='Reinhardt'
        )
        user.private = True
        user.save()
        mes = factories.FoiMessageFactory.create(
            content_hidden=True,
            sender_user=user
        )
        response = self.client.get('/api/v1/message/%d/' % mes.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, user.username)
        self.assertNotContains(response, user.first_name)

    def test_search(self):
        response = self.client.get('/api/v1/request/search/?q=Number')
        self.assertEqual(response.status_code, 200)

    def test_search_similar(self):
        simple_search_url = '/api/v1/request/simplesearch/?format=json'
        response = self.client.get(simple_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{"objects": []}', response.content.decode('utf-8'))
        self.assertEqual(response['Content-Type'], 'application/json')
        req = FoiRequest.objects.all()[0]
        factories.rebuild_index()
        response = self.client.get('%s&%s' % (
            simple_search_url, urlencode({'q': req.title})
        ))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('title', content)
        self.assertIn('description', content)
        self.assertIn('public_body_name', content)
        self.assertIn('url', content)
