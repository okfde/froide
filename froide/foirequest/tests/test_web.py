from __future__ import with_statement

from django.test import TestCase
from django.core.urlresolvers import reverse

from publicbody.models import PublicBody
from foirequest.models import FoiRequest

class WebTest(TestCase):
    fixtures = ['auth.json', 'foirequest.json']

    def test_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_request(self):
        response = self.client.get(reverse('foirequest-make_request'))
        self.assertEqual(response.status_code, 200)

    def test_request_to(self):
        p = PublicBody.objects.all()[0]
        response = self.client.get(reverse('foirequest-make_request', kwargs={'public_body': p.slug}))
        self.assertEqual(response.status_code, 200)

    def test_list_requests(self):
        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)

    def test_show_request(self):
        req = FoiRequest.objects.all()[0]
        response = self.client.get(reverse('foirequest-show', kwargs={"slug": req.slug+"-garbage"}))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse('foirequest-show', kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
        req.visibility = 1
        req.public = False
        req.save()
        response = self.client.get(reverse('foirequest-show', kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)
        self.client.login(username="sw", password="froide")
        response = self.client.get(reverse('foirequest-show', kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)

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
