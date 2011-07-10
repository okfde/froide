from django.test import TestCase
from django.core.urlresolvers import reverse

from publicbody.models import PublicBody, FoiLaw

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

    def test_topic(self):
        pb = PublicBody.objects.all()[0]
        topic = pb.topic
        response = self.client.get(reverse('publicbody-show_topic',
            kwargs={"topic": topic.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(pb.name, response.content.decode('utf-8'))

    def test_autocomplete(self):
        import json
        response = self.client.get(
                reverse('publicbody-autocomplete')+"?query=abc")
        self.assertEqual(response.status_code, 200)
        obj = json.loads(response.content.decode('utf-8'))
        self.assertIn(u'Selbstschutzschule', obj['suggestions'][0])
        self.assertIn(u'Selbstschutzschule', obj['data'][0]['name'])


    def test_csv(self):
        csv = PublicBody.export_csv()
        self.assertTrue(csv)

    def test_search(self):
        response = self.client.get(reverse('publicbody-search')+"?q=abc")
        self.assertIn("Selbstschutzschule", response.content)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_show_law(self):
        law = FoiLaw.objects.filter(meta=False)[0]
        response = self.client.get(reverse('publicbody-foilaw-show', kwargs={"slug": law.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(law.name, response.content)

