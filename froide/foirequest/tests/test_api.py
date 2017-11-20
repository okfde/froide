from __future__ import unicode_literals

from datetime import timedelta
import json

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.test import TestCase
from django.core import mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from oauth2_provider.models import get_access_token_model, get_application_model

from froide.publicbody.models import PublicBody
from froide.foirequest.tests import factories
from froide.foirequest.models import FoiRequest, FoiAttachment


User = get_user_model()
Application = get_application_model()
AccessToken = get_access_token_model()


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
        search_url = '/api/v1/request/search/'
        response = self.client.get(search_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"objects":[]')
        self.assertEqual(response['Content-Type'], 'application/json')
        req = FoiRequest.objects.all()[0]
        factories.rebuild_index()
        response = self.client.get('%s?%s' % (
            search_url, urlencode({'q': req.title})
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'title')
        self.assertContains(response, 'description')


class OAuthApiTest(TestCase):
    def setUp(self):
        factories.make_world()
        self.test_user = User.objects.get(username='dummy')
        self.dev_user = User.objects.create_user("dev@example.com", "dev_user", "123456")

        self.application = Application.objects.create(
            name="Test Application",
            redirect_uris="http://localhost http://example.com http://example.org",
            user=self.dev_user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )

        self.access_token = AccessToken.objects.create(
            user=self.test_user,
            scope="read:user",
            expires=timezone.now() + timedelta(seconds=300),
            token="secret-access-token-key",
            application=self.application
        )

        self.req = factories.FoiRequestFactory.create(
            visibility=FoiRequest.VISIBLE_TO_REQUESTER,
            user=self.test_user,
            title='permissions required'
        )
        self.mes = factories.FoiMessageFactory.create(
            request=self.req
        )
        self.att = factories.FoiAttachmentFactory.create(
            belongs_to=self.mes,
            approved=False
        )
        self.att2 = factories.FoiAttachmentFactory.create(
            belongs_to=self.mes,
            approved=True
        )
        factories.FoiRequestFactory.create(
            visibility=FoiRequest.VISIBLE_TO_REQUESTER,
            user=self.dev_user,
            title='never shown'
        )
        self.pb = PublicBody.objects.all()[0]
        self.request_list_url = reverse('api:request-list')
        self.message_detail_url = reverse('api:message-detail',
                                          kwargs={'pk': self.mes.pk})

    def _create_authorization_header(self, token):
        return "Bearer {0}".format(token)

    def api_get(self, url):
        auth = self._create_authorization_header(self.access_token.token)
        response = self.client.get(url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)
        return response, json.loads(response.content.decode('utf-8'))

    def api_post(self, url, data):
        auth = self._create_authorization_header(self.access_token.token)
        response = self.client.post(url, json.dumps(data),
            content_type="application/json", HTTP_AUTHORIZATION=auth)
        return response, json.loads(response.content.decode('utf-8'))

    def test_list_public_requests(self):
        self.assertEqual(FoiRequest.objects.all().count(), 3)
        response = self.client.get(self.request_list_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['meta']['total_count'], 1)

    def test_list_private_requests_when_logged_in(self):
        self.client.login(email=self.test_user.email, password='froide')
        response = self.client.get(self.request_list_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['meta']['total_count'], 2)

    def test_list_private_requests_without_scope(self):
        response, result = self.api_get(self.request_list_url)
        self.assertEqual(result['meta']['total_count'], 1)
        self.assertNotContains(response, 'permissions required')
        self.assertNotContains(response, 'never shown')

    def test_list_private_requests_with_scope(self):
        self.access_token.scope = "read:user read:request"
        self.access_token.save()

        response, result = self.api_get(self.request_list_url)
        self.assertEqual(result['meta']['total_count'], 2)
        self.assertContains(response, 'permissions required')
        self.assertNotContains(response, 'never shown')

    def test_filter_other_private_requests(self):
        self.access_token.scope = "read:user read:request"
        self.access_token.save()

        response, result = self.api_get(self.request_list_url + '?user=%s' %
                                        self.dev_user.pk)
        self.assertEqual(result['meta']['total_count'], 0)

    def test_filter_private_requests_without_scope(self):
        response, result = self.api_get(self.request_list_url + '?user=%s' %
                                        self.test_user.pk)
        self.assertEqual(result['meta']['total_count'], 0)

    def test_filter_private_requests_with_scope(self):
        self.access_token.scope = "read:user read:request"
        self.access_token.save()

        response, result = self.api_get(self.request_list_url + '?user=%s' %
                                        self.test_user.pk)
        self.assertEqual(result['meta']['total_count'], 1)

    def test_see_only_approved_attachments(self):
        self.req.visibility = FoiRequest.VISIBLE_TO_PUBLIC
        self.req.save()

        self.assertEqual(FoiAttachment.objects.all().count(), 4)
        response = self.client.get(self.message_detail_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(result['attachments']), 1)

    def test_see_only_approved_attachments_loggedin(self):
        self.req.visibility = FoiRequest.VISIBLE_TO_PUBLIC
        self.req.save()

        self.client.login(email=self.test_user.email, password='froide')
        response = self.client.get(self.message_detail_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(result['attachments']), 2)

    def test_see_only_approved_attachments_without_scope(self):
        self.req.visibility = FoiRequest.VISIBLE_TO_PUBLIC
        self.req.save()

        response, result = self.api_get(self.message_detail_url)
        self.assertEqual(len(result['attachments']), 1)

    def test_see_only_approved_attachments_with_scope(self):
        self.req.visibility = FoiRequest.VISIBLE_TO_PUBLIC
        self.req.save()

        self.access_token.scope = "read:user read:request"
        self.access_token.save()

        response, result = self.api_get(self.message_detail_url)
        self.assertEqual(len(result['attachments']), 2)

    def test_request_creation_not_loggedin(self):
        old_count = FoiRequest.objects.all().count()
        response = self.client.post(self.request_list_url, json.dumps({
            'subject': 'Test',
            'body': 'Testing',
            'publicbodies': [self.pb.pk]
        }), content_type="application/json")
        self.assertEqual(response.status_code, 403)
        new_count = FoiRequest.objects.all().count()
        self.assertEqual(old_count, new_count)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_creation_without_scope(self):
        old_count = FoiRequest.objects.all().count()
        response, result = self.api_post(self.request_list_url, {
            'subject': 'Test',
            'body': 'Testing',
            'publicbodies': [self.pb.pk]
        })
        self.assertEqual(response.status_code, 403)
        new_count = FoiRequest.objects.all().count()
        self.assertEqual(old_count, new_count)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_creation_with_scope(self):
        self.access_token.scope = "read:user make:request"
        self.access_token.save()

        old_count = FoiRequest.objects.all().count()
        mail.outbox = []
        data = {
            'subject': 'OAUth-Test',
            'body': 'Testing',
            'publicbodies': [self.pb.pk],
            'tags': ['test1', 'test2']
        }
        response, result = self.api_post(self.request_list_url, data)
        self.assertEqual(response.status_code, 201)
        new_count = FoiRequest.objects.all().count()
        self.assertEqual(old_count, new_count - 1)
        self.assertEqual(len(mail.outbox), 2)
        new_req = FoiRequest.objects.get(title='OAUth-Test')
        self.assertEqual(set([t.name for t in new_req.tags.all()]),
                         set(data['tags']))

        # Check throttling
        froide_config = dict(settings.FROIDE_CONFIG)
        froide_config['request_throttle'] = [(1, 60), (5, 60 * 60)]
        with self.settings(FROIDE_CONFIG=froide_config):
            response, result = self.api_post(self.request_list_url, {
                'subject': 'Test',
                'body': 'Testing',
                'publicbodies': [self.pb.pk]
            })
        self.assertEqual(response.status_code, 429)
