from __future__ import with_statement

from django.utils.six import text_type as str
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from froide.publicbody.models import PublicBody, PublicBodyTag, Jurisdiction
from froide.foirequest.models import FoiRequest, FoiAttachment
from froide.foirequest.tests import factories


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

    def test_request_prefilled(self):
        p = PublicBody.objects.all()[0]
        response = self.client.get(reverse('foirequest-make_request',
            kwargs={'public_body': p.slug}) + '?body=THEBODY&subject=THESUBJECT')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('THEBODY', content)
        self.assertIn('THESUBJECT', content)

    def test_request_prefilled_redirect(self):
        p = PublicBody.objects.all()[0]
        query = '?body=THEBODY&subject=THESUBJECT'
        response = self.client.get(reverse('foirequest-make_request',
            kwargs={'public_body_id': str(p.pk)}) + query)
        self.assertRedirects(
            response,
            reverse('foirequest-make_request', kwargs={
                'public_body': p.slug
                }) + query,
            status_code=301
        )

    def test_list_requests(self):
        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)
        for urlpart, _, status in FoiRequest.get_status_url():
            response = self.client.get(reverse('foirequest-list',
                kwargs={"status": str(urlpart)}))
            self.assertEqual(response.status_code, 200)
        url = reverse('foirequest-list',
                kwargs={"status": 'successful'})
        url = url.replace('successful', 'non-existing')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        for topic in PublicBodyTag.objects.filter(is_topic=True):
            response = self.client.get(reverse('foirequest-list',
                kwargs={"topic": topic.slug}))
            self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('foirequest-list_not_foi'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('foirequest-list') + '?page=99999')
        self.assertEqual(response.status_code, 200)

    def test_list_jurisdiction_requests(self):
        juris = Jurisdiction.objects.all()[0]
        response = self.client.get(reverse('foirequest-list'),
                kwargs={'jurisdiction': juris.slug})
        self.assertEqual(response.status_code, 200)
        for urlpart, _, status in FoiRequest.get_status_url():
            response = self.client.get(reverse('foirequest-list',
                kwargs={"status": urlpart, 'jurisdiction': juris.slug}))
            self.assertEqual(response.status_code, 200)

        for topic in PublicBodyTag.objects.filter(is_topic=True):
            response = self.client.get(reverse('foirequest-list',
                kwargs={"topic": topic.slug, 'jurisdiction': juris.slug}))
            self.assertEqual(response.status_code, 200)

    def test_tagged_requests(self):
        tag_slug = 'awesome'
        response = self.client.get(reverse('foirequest-list', kwargs={"tag": tag_slug}))
        self.assertEqual(response.status_code, 404)
        req = FoiRequest.published.all()[0]
        req.tags.add(tag_slug)
        req.save()
        response = self.client.get(reverse('foirequest-list', kwargs={"tag": tag_slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(req.title, response.content.decode('utf-8'))
        response = self.client.get(reverse('foirequest-list_feed', kwargs={
            'tag': tag_slug
        }))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-list_feed_atom', kwargs={
            'tag': tag_slug
        }))
        self.assertEqual(response.status_code, 200)

    def test_publicbody_requests(self):
        fake_slug = 'fake-slug'
        response = self.client.get(reverse('foirequest-list', kwargs={"public_body": fake_slug}))
        self.assertEqual(response.status_code, 404)
        req = FoiRequest.published.all()[0]
        pb = req.public_body
        response = self.client.get(reverse('foirequest-list', kwargs={"public_body": pb.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(req.title, response.content.decode('utf-8'))
        response = self.client.get(reverse('foirequest-list_feed', kwargs={"public_body": pb.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-list_feed_atom', kwargs={"public_body": pb.slug}))
        self.assertEqual(response.status_code, 200)

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
        self.assertRedirects(response, req.get_absolute_url())
        # Shortlinks may end in /
        response = self.client.get(reverse('foirequest-shortlink',
                kwargs={"obj_id": req.id}) + '/')
        self.assertRedirects(response, req.get_absolute_url())
        req.visibility = FoiRequest.VISIBLE_TO_REQUESTER
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

        topic = PublicBodyTag.objects.filter(is_topic=True)[0]
        response = self.client.get(reverse('foirequest-list_feed', kwargs={
            'jurisdiction': juris.slug,
            'topic': topic.slug
        }))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-list_feed_atom', kwargs={
            'jurisdiction': juris.slug,
            'topic': topic.slug
        }))
        self.assertEqual(response.status_code, 200)

        status = FoiRequest.get_status_url()[0][0]
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


class PerformanceTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_queries_foirequest(self):
        """
        FoiRequest page should query for non-loggedin users
        - FoiRequest (+1)
        - FoiMessages of that request (+1)
        - FoiAttachments of that request (+1)
        - FoiEvents of that request (+1)
        - FoiRequestFollowerCount (+1)
        - Tags (+1)
        - ContentType + Comments for each FoiMessage (+3)
        """
        req = factories.FoiRequestFactory.create(site=self.site)
        factories.FoiMessageFactory.create(request=req)
        mes2 = factories.FoiMessageFactory.create(request=req)
        factories.FoiAttachmentFactory.create(belongs_to=mes2)
        ContentType.objects.clear_cache()
        with self.assertNumQueries(9):
            self.client.get(req.get_absolute_url())

    def test_queries_foirequest_loggedin(self):
        """
        FoiRequest page should query for non-staff loggedin users
        - Django session + Django user (+3)
        - FoiRequest (+1)
        - FoiMessages of that request (+1)
        - FoiAttachments of that request (+1)
        - FoiEvents of that request (+1)
        - FoiRequestFollowerCount + if following (+2)
        - Tags (+1)
        - ContentType + Comments for each FoiMessage (+3)
        """
        req = factories.FoiRequestFactory.create(site=self.site)
        factories.FoiMessageFactory.create(request=req)
        mes2 = factories.FoiMessageFactory.create(request=req)
        factories.FoiAttachmentFactory.create(belongs_to=mes2)
        self.client.login(username='dummy', password='froide')
        ContentType.objects.clear_cache()
        with self.assertNumQueries(12):
            self.client.get(req.get_absolute_url())
