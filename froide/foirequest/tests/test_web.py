from __future__ import with_statement

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings

from froide.publicbody.models import PublicBody, PublicBodyTopic, Jurisdiction
from froide.foirequest.models import FoiRequest, FoiAttachment
from froide.foirequest.tests import factories
from froide.helper.test_utils import skip_if_environ


class WebTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_request(self):
        response = self.client.get(reverse('foirequest-make_request'))
        self.assertEqual(response.status_code, 200)

    def test_request_to(self):
        p = PublicBody.objects.all()[0]
        response = self.client.get(reverse('foirequest-make_request',
            kwargs={'public_body': p.slug}))
        self.assertEqual(response.status_code, 200)
        p.email = ""
        p.save()
        response = self.client.get(reverse('foirequest-make_request',
            kwargs={'public_body': p.slug}))
        self.assertEqual(response.status_code, 404)

    def test_list_requests(self):
        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)
        for urlpart, status in FoiRequest.STATUS_URLS:
            response = self.client.get(reverse('foirequest-list',
                kwargs={"status": urlpart}))
            self.assertEqual(response.status_code, 200)

        for topic in PublicBodyTopic.objects.all():
            response = self.client.get(reverse('foirequest-list',
                kwargs={"topic": topic.slug}))
            self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('foirequest-list_not_foi'))
        self.assertEqual(response.status_code, 200)

    def test_list_jurisdiction_requests(self):
        juris = Jurisdiction.objects.all()[0]
        response = self.client.get(reverse('foirequest-list'),
                kwargs={'jurisdiction': juris.slug})
        self.assertEqual(response.status_code, 200)
        for urlpart, status in FoiRequest.STATUS_URLS:
            response = self.client.get(reverse('foirequest-list',
                kwargs={"status": urlpart, 'jurisdiction': juris.slug}))
            self.assertEqual(response.status_code, 200)

        for topic in PublicBodyTopic.objects.all():
            response = self.client.get(reverse('foirequest-list',
                kwargs={"topic": topic.slug, 'jurisdiction': juris.slug}))
            self.assertEqual(response.status_code, 200)

    def test_tagged_requests(self):
        response = self.client.get(reverse('foirequest-list', kwargs={"tag": "awesome"}))
        self.assertEqual(response.status_code, 404)
        req = FoiRequest.published.all()[0]
        req.tags.add('awesome')
        req.save()
        response = self.client.get(reverse('foirequest-list', kwargs={"tag": "awesome"}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(req.title, response.content.decode('utf-8'))

    def test_list_no_identical(self):
        factories.FoiRequestFactory.create(site=self.site)
        reqs = FoiRequest.published.all()
        req1 = reqs[0]
        req2 = reqs[1]
        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(req1.title, response.content.decode('utf-8'))
        self.assertIn(req2.title, response.content.decode('utf-8'))
        req1.same_as = req2
        req1.save()
        req2.same_as_count = 1
        req2.save()
        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(req1.title, response.content.decode('utf-8'))
        self.assertIn(req2.title, response.content.decode('utf-8'))

    def test_show_request(self):
        req = FoiRequest.objects.all()[0]
        response = self.client.get(reverse('foirequest-show',
                kwargs={"slug": req.slug + "-garbage"}))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse('foirequest-show',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
        req.visibility = 1
        req.save()
        response = self.client.get(reverse('foirequest-show',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)
        self.client.login(username="sw", password="froide")
        response = self.client.get(reverse('foirequest-show',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)

    def test_short_link_request(self):
        req = FoiRequest.objects.all()[0]
        response = self.client.get(reverse('foirequest-shortlink',
                kwargs={"obj_id": 0}))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse('foirequest-shortlink',
                kwargs={"obj_id": req.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith(req.get_absolute_url()))
        req.visibility = 1
        req.save()
        response = self.client.get(reverse('foirequest-shortlink',
                kwargs={"obj_id": req.id}))
        self.assertEqual(response.status_code, 403)

    def test_auth_links(self):
        req = FoiRequest.objects.all()[0]
        req.visibility = 1
        req.save()
        response = self.client.get(reverse('foirequest-show',
            kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse('foirequest-auth',
            kwargs={'obj_id': req.id, 'code': '0a'}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse('foirequest-auth',
            kwargs={'obj_id': req.id, 'code': req.get_auth_code()}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith(req.get_absolute_url()))
        # Check logged in with wrong code
        self.client.login(username="sw", password="froide")
        response = self.client.get(reverse('foirequest-auth',
            kwargs={'obj_id': req.id, 'code': '0a'}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith(req.get_absolute_url()))

    def test_feed(self):
        response = self.client.get(reverse('foirequest-feed_latest'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-feed_latest_atom'))
        self.assertEqual(response.status_code, 200)
        req = FoiRequest.objects.all()[0]
        response = self.client.get(reverse('foirequest-feed_atom',
            kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-feed',
            kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)

    def test_unchecked(self):
        response = self.client.get(reverse('foirequest-list_unchecked'))
        self.assertEqual(response.status_code, 403)
        self.client.login(username="dummy", password="froide")
        response = self.client.get(reverse('foirequest-list_unchecked'))
        self.assertEqual(response.status_code, 403)
        self.client.logout()
        self.client.login(username="sw", password="froide")
        response = self.client.get(reverse('foirequest-list_unchecked'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 403)
        self.client.login(username="dummy", password="froide")
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 403)
        self.client.logout()
        self.client.login(username="sw", password="froide")
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    @skip_if_environ('FROIDE_SKIP_SOLR')
    def test_search_similar(self):
        response = self.client.get(reverse('foirequest-search_similar'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual('[]', response.content.decode('utf-8'))
        self.assertEqual(response['Content-Type'], 'application/json')
        response = self.client.get(reverse('foirequest-search_similar') + '?q=Bundes')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('title', content)
        self.assertIn('description', content)
        self.assertIn('public_body_name', content)
        self.assertIn('url', content)

    @skip_if_environ('FROIDE_SKIP_SOLR')
    def test_search(self):
        response = self.client.get(reverse('foirequest-search'))
        self.assertEqual(response.status_code, 200)


class MediaServingTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_request_not_public(self):
        att = FoiAttachment.objects.filter(approved=True)[0]
        req = att.belongs_to.request
        req.visibility = 1
        req.save()
        response = self.client.get(att.get_absolute_url())
        self.assertEqual(response.status_code, 403)
        self.client.login(username='sw', password='froide')
        response = self.client.get(att.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn('X-Accel-Redirect', response)
        self.assertEqual(response['X-Accel-Redirect'], '%s%s' % (
            settings.X_ACCEL_REDIRECT_PREFIX, att.file.url))

    def test_attachment_not_approved(self):
        att = FoiAttachment.objects.filter(approved=False)[0]
        response = self.client.get(att.get_absolute_url())
        self.assertEqual(response.status_code, 403)
        self.client.login(username='sw', password='froide')
        response = self.client.get(att.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_request_public(self):
        att = FoiAttachment.objects.filter(approved=True)[0]
        response = self.client.get(att.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        response = self.client.get(att.get_absolute_url() + 'a')
        self.assertEqual(response.status_code, 404)
