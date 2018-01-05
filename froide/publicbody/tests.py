from __future__ import unicode_literals

import json
import tempfile

from django.utils import six
from django.test import TestCase
from django.urls import reverse

from froide.foirequest.tests import factories
from froide.helper.csv_utils import export_csv_bytes

from .models import PublicBody, FoiLaw, Jurisdiction
from .csv_import import CSVImporter


class PublicBodyTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_web_page(self):
        response = self.client.get(reverse('publicbody-list'))
        self.assertEqual(response.status_code, 200)
        pb = PublicBody.objects.all()[0]
        category = factories.CategoryFactory.create()
        pb.categories.add(category)
        response = self.client.get(reverse('publicbody-list', kwargs={
            'topic': category.slug
        }))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, pb.name)
        response = self.client.get(reverse('publicbody-list', kwargs={
            'jurisdiction': pb.jurisdiction.slug
        }))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, pb.name)
        response = self.client.get(reverse('publicbody-list', kwargs={
            'jurisdiction': pb.jurisdiction.slug,
            'topic': category.slug
        }))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, pb.name)
        response = self.client.get(reverse('publicbody-show',
                kwargs={"slug": pb.slug}))
        self.assertEqual(response.status_code, 200)

    def test_csv(self):
        csv = export_csv_bytes(PublicBody.export_csv(PublicBody.objects.all()))
        self.assertEqual(PublicBody.objects.all().count() + 1,
            len(csv.splitlines()))

    def test_csv_export_import(self):
        csv = export_csv_bytes(PublicBody.export_csv(PublicBody.objects.all()))
        prev_count = PublicBody.objects.all().count()
        imp = CSVImporter()
        csv_file = six.BytesIO(csv)
        imp.import_from_file(csv_file)
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count, prev_count)

    def test_csv_existing_import(self):
        factories.PublicBodyFactory.create(site=self.site, name='Public Body 76 X')
        # reenable when django-taggit support atomic transaction wrapping
        # factories.PublicBodyTagFactory.create(slug='public-body-topic-76-x', is_topic=True)

        prev_count = PublicBody.objects.all().count()
        # Existing entity via slug, no id reference
        csv = '''name,email,jurisdiction__slug,other_names,description,tags,url,parent__name,classification,contact,address,website_dump,request_note
Public Body 76 X,pb-76@76.example.com,bund,,,public-body-topic-76-x,http://example.com,,Ministry,Some contact stuff,An address,,'''
        imp = CSVImporter()
        imp.import_from_file(six.BytesIO(csv.encode('utf-8')))
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count, prev_count)

    def test_csv_new_import(self):
        prev_count = PublicBody.objects.all().count()
        csv = '''name,email,jurisdiction__slug,other_names,description,tags,url,parent__name,classification,contact,address,website_dump,request_note
Public Body X 76,pb-76@76.example.com,bund,,,,http://example.com,,Ministry,Some contact stuff,An address,,'''
        imp = CSVImporter()
        imp.import_from_file(six.BytesIO(csv.encode('utf-8')))
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count - 1, prev_count)

    def test_csv_command(self):
        from django.core.management import call_command
        csv_file = tempfile.NamedTemporaryFile()
        csv_file.write(export_csv_bytes(PublicBody.export_csv(PublicBody.objects.all())))
        csv_file.flush()

        call_command('import_csv', csv_file.name)

        csv_file.close()

    def test_csv_import_request(self):
        url = reverse('publicbody-import')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        self.client.login(email='dummy@example.org', password='froide')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(email='info@fragdenstaat.de', password='froide')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        response = self.client.post(url, {'url': 'test'})
        self.assertEqual(response.status_code, 302)

    def test_show_law(self):
        law = FoiLaw.objects.filter(meta=False)[0]
        self.assertIn(law.jurisdiction.name, str(law))
        response = self.client.get(law.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, law.name)

    def test_show_jurisdiction(self):
        juris = Jurisdiction.objects.all()[0]
        response = self.client.get(juris.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, juris.name)
        new_juris = factories.JurisdictionFactory.create(name='peculiar')
        response = self.client.get(new_juris.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_show_public_bodies_of_jurisdiction(self):
        juris = Jurisdiction.objects.all()[0]
        response = self.client.get(reverse('publicbody-list',
                kwargs={'jurisdiction': juris.slug}))
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

    def test_autocomplete(self):
        pb = PublicBody.objects.all()[0]
        factories.rebuild_index()

        response = self.client.get('%s?q=%s' % (
                '/api/v1/publicbody/search/', pb.name))
        self.assertEqual(response.status_code, 200)
        obj = json.loads(response.content.decode('utf-8'))
        self.assertIn(pb.name, obj['objects']['results'][0]['name'])
        response = self.client.get('%s?query=%s&jurisdiction=non_existant' % (
                '/api/v1/publicbody/search/', pb.name))
        self.assertEqual(response.status_code, 200)
        obj = json.loads(response.content.decode('utf-8'))
        self.assertEqual(obj['objects']['results'], [])
