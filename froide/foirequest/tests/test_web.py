from __future__ import with_statement

from django.test import TestCase
from django.core.urlresolvers import reverse

from publicbody.models import PublicBody

class WebTest(TestCase):
    fixtures = ['publicbodies.json']

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
