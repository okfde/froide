import unittest

from mock import patch

from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from django.test.utils import override_settings
from django.contrib.contenttypes.models import ContentType

from froide.publicbody.models import PublicBody, Category, Jurisdiction
from froide.foirequest.models import FoiRequest, FoiAttachment
from froide.foirequest.tests import factories
from froide.foirequest.filters import FOIREQUEST_FILTER_DICT, FOIREQUEST_FILTERS
from froide.helper.auth import clear_lru_caches
from froide.helper.search.signal_processor import realtime_search


class TestCaseHelpers():
    def assertForbidden(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account-login'), response['Location'])
        self.assertIn('?next=', response['Location'])


class WebTest(TestCaseHelpers, TestCase):
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
            kwargs={'publicbody_slug': p.slug}))
        self.assertEqual(response.status_code, 200)
        p.email = ""
        p.save()
        response = self.client.get(reverse('foirequest-make_request',
            kwargs={'publicbody_slug': p.slug}))
        self.assertEqual(response.status_code, 404)

    def test_request_prefilled(self):
        p = PublicBody.objects.all()[0]
        response = self.client.get(reverse('foirequest-make_request',
            kwargs={'publicbody_slug': p.slug}) + '?body=THEBODY&subject=THESUBJECT')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('THEBODY', content)
        self.assertIn('THESUBJECT', content)

    @unittest.skip('No longer redirect to slug on pb ids')
    def test_request_prefilled_redirect(self):
        p = PublicBody.objects.all()[0]
        query = '?body=THEBODY&subject=THESUBJECT'
        response = self.client.get(reverse('foirequest-make_request',
            kwargs={'publicbody_ids': str(p.pk)}) + query)
        self.assertRedirects(
            response,
            reverse('foirequest-make_request', kwargs={
                'publicbody_slug': p.slug
                }) + query,
            status_code=200
        )

    def test_list_requests(self):
        factories.rebuild_index()
        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)
        for urlpart in FOIREQUEST_FILTER_DICT:
            response = self.client.get(reverse('foirequest-list',
                kwargs={"status": str(urlpart)}))
            self.assertEqual(response.status_code, 200)

        for topic in Category.objects.filter(is_topic=True):
            response = self.client.get(reverse('foirequest-list',
                kwargs={"category": topic.slug}))
            self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('foirequest-list') + '?page=99999')
        self.assertEqual(response.status_code, 404)

    def test_list_jurisdiction_requests(self):
        factories.rebuild_index()
        juris = Jurisdiction.objects.all()[0]
        response = self.client.get(reverse('foirequest-list'),
                kwargs={'jurisdiction': juris.slug})
        self.assertEqual(response.status_code, 200)
        for urlpart in FOIREQUEST_FILTER_DICT:
            response = self.client.get(reverse('foirequest-list',
                kwargs={"status": urlpart, 'jurisdiction': juris.slug}))
            self.assertEqual(response.status_code, 200)

        for topic in Category.objects.filter(is_topic=True):
            response = self.client.get(reverse('foirequest-list',
                kwargs={"category": topic.slug, 'jurisdiction': juris.slug}))
            self.assertEqual(response.status_code, 200)

    def test_tagged_requests(self):
        tag_slug = 'awesome'
        req = FoiRequest.published.all()[0]
        req.tags.add(tag_slug)
        req.save()
        factories.rebuild_index()

        response = self.client.get(reverse('foirequest-list', kwargs={"tag": tag_slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, req.title)
        response = self.client.get(reverse('foirequest-list_feed', kwargs={
            'tag': tag_slug
        }))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-list_feed_atom', kwargs={
            'tag': tag_slug
        }))
        self.assertEqual(response.status_code, 200)

    def test_publicbody_requests(self):
        factories.rebuild_index()
        req = FoiRequest.published.all()[0]
        pb = req.public_body
        response = self.client.get(reverse('foirequest-list', kwargs={"publicbody": pb.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, req.title)
        response = self.client.get(reverse('foirequest-list_feed', kwargs={"publicbody": pb.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-list_feed_atom', kwargs={"publicbody": pb.slug}))
        self.assertEqual(response.status_code, 200)

    def test_list_no_identical(self):
        factories.FoiRequestFactory.create(site=self.site)
        factories.rebuild_index()
        reqs = FoiRequest.published.all()
        req1 = reqs[0]
        req2 = reqs[1]
        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, req1.title)
        self.assertContains(response, req2.title)
        with realtime_search(self):
            req1.same_as = req2
            req1.save()
            req2.same_as_count = 1
            req2.save()

        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, req1.title)
        self.assertContains(response, req2.title)

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
        self.assertForbidden(response)
        self.client.login(email="info@fragdenstaat.de", password="froide")
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
        self.assertRedirects(response, req.get_absolute_url())
        # Shortlinks may end in /
        response = self.client.get(reverse('foirequest-shortlink',
                kwargs={"obj_id": req.id}) + '/')
        self.assertRedirects(response, req.get_absolute_url())
        req.visibility = FoiRequest.VISIBLE_TO_REQUESTER
        req.save()
        response = self.client.get(reverse('foirequest-shortlink',
                kwargs={"obj_id": req.id}))
        self.assertForbidden(response)

    def test_auth_links(self):
        from froide.foirequest.auth import get_foirequest_auth_code

        req = FoiRequest.objects.all()[0]
        req.visibility = 1
        req.save()
        response = self.client.get(reverse('foirequest-show',
            kwargs={"slug": req.slug}))
        self.assertForbidden(response)
        response = self.client.get(reverse('foirequest-auth',
            kwargs={'obj_id': req.id, 'code': '0a'}))
        self.assertForbidden(response)
        response = self.client.get(reverse('foirequest-auth',
            kwargs={
                'obj_id': req.id,
                'code': get_foirequest_auth_code(req)
            }))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith(req.get_absolute_url()))
        # Check logged in with wrong code
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.get(reverse('foirequest-auth',
            kwargs={'obj_id': req.id, 'code': '0a'}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith(req.get_absolute_url()))

    def test_feed(self):
        factories.rebuild_index()

        response = self.client.get(reverse('foirequest-feed_latest'))
        self.assertRedirects(response, reverse('foirequest-list_feed'),
            status_code=301)
        response = self.client.get(reverse('foirequest-feed_latest_atom'))
        self.assertRedirects(response, reverse('foirequest-list_feed_atom'),
            status_code=301)

        response = self.client.get(reverse('foirequest-list_feed'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-list_feed_atom'))
        self.assertEqual(response.status_code, 200)

        juris = Jurisdiction.objects.all()[0]
        response = self.client.get(reverse('foirequest-list_feed', kwargs={
            'jurisdiction': juris.slug
        }))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-list_feed_atom', kwargs={
            'jurisdiction': juris.slug
        }))
        self.assertEqual(response.status_code, 200)

        topic = Category.objects.filter(is_topic=True)[0]
        response = self.client.get(reverse('foirequest-list_feed', kwargs={
            'jurisdiction': juris.slug,
            'category': topic.slug
        }))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-list_feed_atom', kwargs={
            'jurisdiction': juris.slug,
            'category': topic.slug
        }))
        self.assertEqual(response.status_code, 200)

        status = FOIREQUEST_FILTERS[0][0]
        response = self.client.get(reverse('foirequest-list_feed', kwargs={
            'jurisdiction': juris.slug,
            'status': status
        }))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-list_feed_atom', kwargs={
            'jurisdiction': juris.slug,
            'status': status
        }))
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
        self.assertForbidden(response)
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.get(reverse('foirequest-list_unchecked'))
        self.assertEqual(response.status_code, 403)
        self.client.logout()
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.get(reverse('foirequest-list_unchecked'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard(self):
        response = self.client.get(reverse('dashboard'))
        self.assertForbidden(response)
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 403)
        self.client.logout()
        self.client.login(email="info@fragdenstaat.de", password="froide")
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_search(self):
        response = self.client.get(reverse('foirequest-search'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('foirequest-list'), response['Location'])


MEDIA_DOMAIN = 'media.frag-den-staat.de'


class MediaServingTest(TestCaseHelpers, TestCase):
    def setUp(self):
        clear_lru_caches()
        self.site = factories.make_world()

    @override_settings(
        SITE_URL='https://fragdenstaat.de',
        MEDIA_URL='https://' + MEDIA_DOMAIN + '/files/',
        ALLOWED_HOSTS=('fragdenstaat.de', MEDIA_DOMAIN),
    )
    @patch('froide.foirequest.auth.AttachmentCrossDomainMediaAuth.SITE_URL',
           'https://fragdenstaat.de')
    def test_request_not_public(self):
        att = FoiAttachment.objects.filter(approved=True)[0]
        req = att.belongs_to.request
        req.visibility = 1
        req.save()
        response = self.client.get(
            att.get_absolute_domain_auth_url(),
            HTTP_HOST='fragdenstaat.de'
        )
        self.assertForbidden(response)
        self.client.login(email='info@fragdenstaat.de', password='froide')
        response = self.client.get(
            att.get_absolute_domain_auth_url(),
            HTTP_HOST='fragdenstaat.de'
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(MEDIA_DOMAIN, response['Location'])
        response = self.client.get(
            response['Location'],
            HTTP_HOST=MEDIA_DOMAIN
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('X-Accel-Redirect', response)
        self.assertEqual(response['X-Accel-Redirect'], '%s%s' % (
            settings.INTERNAL_MEDIA_PREFIX, att.file.name))

    @override_settings(
        SITE_URL='https://fragdenstaat.de',
        MEDIA_URL='https://' + MEDIA_DOMAIN + '/files/',
        ALLOWED_HOSTS=('fragdenstaat.de', MEDIA_DOMAIN)
    )
    def test_request_media_tokens(self):
        att = FoiAttachment.objects.filter(approved=True)[0]
        req = att.belongs_to.request
        req.visibility = 1
        req.save()
        response = self.client.get(
            att.get_absolute_domain_auth_url(),
            HTTP_HOST='fragdenstaat.de'
        )
        self.assertForbidden(response)
        loggedin = self.client.login(
            email='info@fragdenstaat.de', password='froide'
        )
        self.assertTrue(loggedin)

        response = self.client.get(
            att.get_absolute_domain_auth_url().replace('?download', ''),
            follow=False,
            HTTP_HOST='fragdenstaat.de',
        )
        # permanent redirect to attachment page if no refresh
        self.assertEqual(response.status_code, 301)
        redirect_url = response['Location']
        self.assertEqual(redirect_url, att.get_absolute_url())

        # Simulate media refresh redirect
        response = self.client.get(
            att.get_absolute_domain_auth_url(),
            follow=False,
            HTTP_HOST='fragdenstaat.de',
        )
        # temporary redirect to media file
        self.assertEqual(response.status_code, 302)
        redirect_url = response['Location']

        _, _, domain, path = redirect_url.split('/', 3)
        response = self.client.get(
            '/' + path + 'a',  # break signature
            follow=False,
            HTTP_HOST=domain,
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.get(
            '/' + path,
            follow=False,
            HTTP_HOST=domain,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Accel-Redirect'], '%s%s' % (
            settings.INTERNAL_MEDIA_PREFIX, att.file.name))
        self.assertEqual(response['Link'], '<{}>; rel="canonical"'.format(
            att.get_absolute_domain_url()
        ))

    @override_settings(
        SITE_URL='https://fragdenstaat.de',
        MEDIA_URL='https://' + MEDIA_DOMAIN + '/files/',
        ALLOWED_HOSTS=('fragdenstaat.de', MEDIA_DOMAIN),
        FOI_MEDIA_TOKEN_EXPIRY=0
    )
    @patch('froide.foirequest.auth.AttachmentCrossDomainMediaAuth.TOKEN_MAX_AGE_SECONDS',
           0)
    @patch('froide.foirequest.auth.AttachmentCrossDomainMediaAuth.SITE_URL',
           'https://fragdenstaat.de')
    def test_request_media_tokens_expired(self):
        att = FoiAttachment.objects.filter(approved=True)[0]
        req = att.belongs_to.request
        req.visibility = 1
        req.save()

        self.client.login(email='info@fragdenstaat.de', password='froide')

        response = self.client.get(
            att.get_absolute_domain_auth_url(),
            follow=False,
            HTTP_HOST='fragdenstaat.de',
        )
        self.assertEqual(response.status_code, 302)
        redirect_url = response['Location']
        _, _, domain, path = redirect_url.split('/', 3)

        response = self.client.get(
            '/' + path,
            follow=False,
            HTTP_HOST=domain,
        )
        self.assertEqual(response.status_code, 302)
        # Redirect back for re-authenticating
        redirect_url = response['Location']
        _, _, domain, path = redirect_url.split('/', 3)
        self.assertEqual(domain, 'fragdenstaat.de')
        self.assertIn('/' + path, att.get_absolute_domain_auth_url())

    def test_attachment_not_approved(self):
        att = FoiAttachment.objects.filter(approved=False)[0]
        response = self.client.get(att.get_absolute_url())
        self.assertForbidden(response)
        self.client.login(email='info@fragdenstaat.de', password='froide')
        response = self.client.get(att.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_request_public(self):
        att = FoiAttachment.objects.filter(approved=True)[0]
        response = self.client.get(att.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        response = self.client.get(att.get_absolute_url() + 'a')
        self.assertEqual(response.status_code, 404)

    def test_attachment_empty(self):
        att = FoiAttachment.objects.filter(approved=True)[0]
        att.file = ''
        att.save()
        response = self.client.get(att.get_absolute_domain_auth_url())
        self.assertEqual(response.status_code, 404)

    def test_attachment_pending(self):
        att = FoiAttachment.objects.filter(approved=True)[0]
        att.pending = True
        att.save()
        response = self.client.get(att.get_absolute_domain_auth_url())
        self.assertEqual(response.status_code, 404)


class PerformanceTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_queries_foirequest(self):
        """
        FoiRequest page should query for non-loggedin users
        - FoiRequest (+1)
        - FoiRequest Tags (+1)
        - FoiMessages of that request (+1)
        - FoiAttachments of that request (+1)
        - FoiEvents of that request (+1)
        - FoiRequestFollowerCount (+1)
        - Delivery Status (+1)
        - Guides (+1)
        - ContentType + Comments for each FoiMessage (+2)
        """
        req = factories.FoiRequestFactory.create(site=self.site)
        factories.FoiMessageFactory.create(request=req, is_response=False)
        mes2 = factories.FoiMessageFactory.create(request=req)
        factories.FoiAttachmentFactory.create(belongs_to=mes2)
        ContentType.objects.clear_cache()
        with self.assertNumQueries(10):
            self.client.get(req.get_absolute_url())

    def test_queries_foirequest_loggedin(self):
        """
        FoiRequest page should query for non-staff loggedin users
        - Django session + Django user (+3)
        - FoiRequest (+1)
        - FoiRequest Tags (+1)
        - FoiMessages of that request (+1)
        - FoiAttachments of that request (+1)
        - FoiEvents of that request (+1)
        - FoiRequestFollowerCount + if following (+2)
        - Delivery Status (+1)
        - Guides (+1)
        - ContentType + Comments for each FoiMessage (+2)
        """
        TOTAL_EXPECTED_REQUESTS = 13
        req = factories.FoiRequestFactory.create(site=self.site)
        factories.FoiMessageFactory.create(request=req, is_response=False)
        mes2 = factories.FoiMessageFactory.create(request=req)
        factories.FoiAttachmentFactory.create(belongs_to=mes2)
        self.client.login(email='dummy@example.org', password='froide')
        ContentType.objects.clear_cache()
        with self.assertNumQueries(TOTAL_EXPECTED_REQUESTS):
            self.client.get(req.get_absolute_url())
