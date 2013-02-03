from django.test import TestCase
from django.core.urlresolvers import reverse

from froide.foirequest.tests import factories
from froide.helper.test_utils import skip_if_environ

from .models import PublicBody, FoiLaw


class PublicBodyTest(TestCase):
    def setUp(self):
        factories.make_world()

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

    @skip_if_environ('FROIDE_SKIP_SEARCH')
    def test_autocomplete(self):
        import json
        pb = PublicBody.objects.all()[0]
        response = self.client.get('%s?query=%s' % (
                reverse('publicbody-autocomplete'), pb.name))
        self.assertEqual(response.status_code, 200)
        obj = json.loads(response.content.decode('utf-8'))
        self.assertIn(pb.name, obj['suggestions'][0])
        self.assertIn(pb.name, obj['data'][0]['name'])
        response = self.client.get('%s?query=%s&jurisdiction=non_existant' % (
                reverse('publicbody-autocomplete'), pb.name))
        self.assertEqual(response.status_code, 200)
        obj = json.loads(response.content.decode('utf-8'))
        self.assertEqual(obj['suggestions'], [])

    def test_csv(self):
        csv = PublicBody.export_csv(PublicBody.objects.all())
        self.assertEqual(PublicBody.objects.all().count() + 1,
            len(csv.splitlines()))

    @skip_if_environ('FROIDE_SKIP_SEARCH')
    def test_search(self):
        pb = PublicBody.objects.all()[0]
        response = self.client.get('%s?q=%s' % (
            reverse('publicbody-search_json'), pb.name[:6]))
        self.assertIn(pb.name, response.content)
        self.assertEqual(response['Content-Type'], 'application/json')
        response = self.client.get('%s?q=%s&jurisdiction=non_existant' % (
            reverse('publicbody-search_json'), pb.name[:6]))
        self.assertEqual("[]", response.content)

    def test_show_law(self):
        law = FoiLaw.objects.filter(meta=False)[0]
        self.assertIn(law.jurisdiction.name, unicode(law))
        response = self.client.get(law.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn(law.name, response.content.decode('utf-8'))
