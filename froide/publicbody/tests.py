from django.test import TestCase
from django.core.urlresolvers import reverse

from publicbody.models import PublicBody

class PublicBodyTest(TestCase):
    fixtures = ['auth_profile.json', 'publicbody.json', 'foirequest.json']

    def test_web_page(self):
        response = self.client.get(reverse('publicbody-list'))
        self.assertEqual(response.status_code, 200)
        pb = PublicBody.objects.all()[0]
        response = self.client.get(reverse('publicbody-show',
                kwargs={"slug": pb.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('publicbody-show_json',
                kwargs={"pk": pb.pk, "format": "json"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('"name":', response.content)
        self.assertIn('"laws": [{', response.content)
        response = self.client.get(reverse('publicbody-show_json',
                kwargs={"slug": pb.slug, "format": "json"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_csv(self):
        csv = PublicBody.export_csv()
        self.assertTrue(csv)

    def test_search(self):
        response = self.client.get(reverse('publicbody-search')+"?q=umwelt")
        self.assertIn("Bundesministerium f\\u00fcr Umwelt", response.content)
        self.assertEqual(response['Content-Type'], 'application/json')
