import StringIO
import tempfile

from django.test import TestCase
from django.core.urlresolvers import reverse

from froide.foirequest.tests import factories
from froide.helper.test_utils import skip_if_environ

from .models import PublicBody, FoiLaw, Jurisdiction
from .csv_import import CSVImporter


class PublicBodyTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

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
        pb = factories.PublicBodyFactory.create(name='specialbody')
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

    def test_csv_export_import(self):
        csv = PublicBody.export_csv(PublicBody.objects.all())
        prev_count = PublicBody.objects.all().count()
        imp = CSVImporter()
        imp.import_from_file(StringIO.StringIO(csv))
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count, prev_count)

    def test_csv_existing_import(self):
        factories.PublicBodyFactory.create(site=self.site, name='Public Body 76 X')
        factories.PublicBodyTopicFactory.create(slug='public-body-topic-76-x')
        prev_count = PublicBody.objects.all().count()
        # Existing entity via slug, no id reference
        csv = '''name,email,jurisdiction__slug,other_names,description,topic__slug,url,parent__name,classification,contact,address,website_dump,request_note
Public Body 76 X,pb-76@76.example.com,bund,,,public-body-topic-76-x,http://example.com,,Ministry,Some contact stuff,An address,,'''
        imp = CSVImporter()
        imp.import_from_file(StringIO.StringIO(csv))
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count, prev_count)

    def test_csv_new_import(self):
        prev_count = PublicBody.objects.all().count()
        csv = '''name,email,jurisdiction__slug,other_names,description,topic__slug,url,parent__name,classification,contact,address,website_dump,request_note
Public Body X 76,pb-76@76.example.com,bund,,,,http://example.com,,Ministry,Some contact stuff,An address,,'''
        imp = CSVImporter()
        imp.import_from_file(StringIO.StringIO(csv))
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count - 1, prev_count)

    def test_command(self):
        from django.core.management import call_command
        csv_file = tempfile.NamedTemporaryFile()
        csv_file.write(PublicBody.export_csv(PublicBody.objects.all()))

        call_command('import_csv', csv_file.name)

        csv_file.close()

    def test_csv_import_request(self):
        url = reverse('publicbody-import')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        self.client.login(username='dummy', password='froide')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username='sw', password='froide')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        response = self.client.post(url, {'url': 'test'})
        self.assertEqual(response.status_code, 302)

    @skip_if_environ('FROIDE_SKIP_SEARCH')
    def test_search(self):
        pb = factories.PublicBodyFactory.create(name='peculiarentity')
        response = self.client.get('%s?q=%s' % (
            reverse('publicbody-search_json'), pb.name))
        self.assertIn(pb.name, response.content)
        self.assertEqual(response['Content-Type'], 'application/json')
        response = self.client.get('%s?q=%s&jurisdiction=non_existant' % (
            reverse('publicbody-search_json'), pb.name))
        self.assertEqual("[]", response.content)

    def test_show_law(self):
        law = FoiLaw.objects.filter(meta=False)[0]
        self.assertIn(law.jurisdiction.name, unicode(law))
        response = self.client.get(law.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn(law.name, response.content.decode('utf-8'))

    def test_show_jurisdiction(self):
        juris = Jurisdiction.objects.all()[0]
        response = self.client.get(juris.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn(juris.name, response.content.decode('utf-8'))
        new_juris = factories.JurisdictionFactory.create(name='peculiar')
        response = self.client.get(new_juris.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_show_public_bodies_of_jurisdiction(self):
        juris = Jurisdiction.objects.all()[0]
        response = self.client.get(reverse('publicbody-show-pb_jurisdiction',
                kwargs={'slug': juris.slug}))
        self.assertEqual(response.status_code, 200)


class ApiTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_list(self):
        response = self.client.get('/api/v1/publicbody/?format=json')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/api/v1/jurisdiction/?format=json')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/api/v1/law/?format=json')
        self.assertEqual(response.status_code, 200)

    def test_detail(self):
        pb = PublicBody.objects.all()[0]
        response = self.client.get('/api/v1/publicbody/%d/?format=json' % pb.pk)
        self.assertEqual(response.status_code, 200)

        law = FoiLaw.objects.all()[0]
        response = self.client.get('/api/v1/law/%d/?format=json' % law.pk)
        self.assertEqual(response.status_code, 200)

        jur = Jurisdiction.objects.all()[0]
        response = self.client.get('/api/v1/jurisdiction/%d/?format=json' % jur.pk)
        self.assertEqual(response.status_code, 200)

    def test_search(self):
        response = self.client.get('/api/v1/publicbody/search/?format=json&q=Body')
        self.assertEqual(response.status_code, 200)
