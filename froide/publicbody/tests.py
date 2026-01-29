import json
import os
import tempfile
from io import BytesIO

from django.contrib.gis.geos import MultiPolygon
from django.test import TestCase
from django.urls import reverse

import pytest

from froide.account.factories import UserFactory
from froide.foirequest.tests.factories import make_world, rebuild_index
from froide.georegion.models import GeoRegion
from froide.helper.csv_utils import export_csv_bytes

from .csv_import import CSVImporter
from .factories import (
    CategoryFactory,
    ClassificationFactory,
    JurisdictionFactory,
    PublicBodyChangeProposalFactory,
    PublicBodyFactory,
)
from .models import FoiLaw, Jurisdiction, PublicBody, PublicBodyChangeProposal


class PublicBodyTest(TestCase):
    def setUp(self):
        self.site = make_world()

    def test_web_page(self):
        pb = PublicBody.objects.all()[0]
        category = CategoryFactory.create(is_topic=True)
        pb.categories.add(category)

        rebuild_index()

        response = self.client.get(reverse("publicbody-list"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse("publicbody-list", kwargs={"category": category.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, pb.name)
        response = self.client.get(
            reverse("publicbody-list", kwargs={"jurisdiction": pb.jurisdiction.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, pb.name)
        response = self.client.get(
            reverse(
                "publicbody-list",
                kwargs={
                    "jurisdiction": pb.jurisdiction.slug,
                    "category": category.slug,
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, pb.name)
        response = self.client.get(
            reverse("publicbody-show", kwargs={"slug": pb.slug, "pk": pb.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_slug_redirect(self):
        pb = PublicBody.objects.all()[0]
        response = self.client.get(reverse("publicbody-show", kwargs={"slug": pb.slug}))
        self.assertRedirects(response, pb.get_absolute_url(), status_code=301)

        response = self.client.get(reverse("publicbody-show", kwargs={"pk": pb.id}))
        self.assertRedirects(response, pb.get_absolute_url(), status_code=301)

        response = self.client.get(
            reverse("publicbody-show", kwargs={"pk": pb.id, "slug": "bad-slug"})
        )
        self.assertRedirects(response, pb.get_absolute_url(), status_code=301)

        response = self.client.get(
            reverse("publicbody-show", kwargs={"pk": "0", "slug": "bad-slug"})
        )
        self.assertEqual(response.status_code, 404)

    def test_publicbody_page_access(self):
        pb = PublicBody.objects.all()[0]
        pb.confirmed = False
        pb.save()
        response = self.client.get(pb.get_absolute_url())
        self.assertEqual(response.status_code, 403)
        self.client.force_login(pb._created_by)
        response = self.client.get(pb.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        superuser = UserFactory.create(is_superuser=True)
        self.client.force_login(superuser)
        response = self.client.get(pb.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_csv(self):
        csv = export_csv_bytes(PublicBody.export_csv(PublicBody.objects.all()))
        self.assertEqual(PublicBody.objects.all().count() + 1, len(csv.splitlines()))

    def test_csv_export_import(self):
        csv = export_csv_bytes(PublicBody.export_csv(PublicBody.objects.all()))
        prev_count = PublicBody.objects.all().count()
        imp = CSVImporter()
        csv_file = BytesIO(csv)
        imp.import_from_file(csv_file)
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count, prev_count)

    def test_csv_existing_import(self):
        classification = ClassificationFactory.create(name="Ministry")
        source_reference = "source:42"
        pb = PublicBodyFactory.create(
            site=self.site,
            name="Public Body 76 X",
            classification=classification,
            source_reference=source_reference,
        )
        georegion_identifier = "01234"
        region = GeoRegion.add_root(
            name="Region 1",
            slug="region-1",
            kind="district",
            region_identifier=georegion_identifier,
            geom=MultiPolygon(),
        )
        pb.regions.add(region)

        prev_count = PublicBody.objects.all().count()
        # Existing entity via id
        imp = CSVImporter()
        csv = """id,name,email,jurisdiction__slug,other_names,description,url,parent__name,classification,contact,address
{},Public Body 76 X,pb-76@76.example.com,bund,,,http://example.com,,Ministry,Some contact stuff,An address""".format(
            pb.id
        )
        imp.import_from_file(BytesIO(csv.encode("utf-8")))
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count, prev_count)

        # Existing entity via source reference
        csv = """name,email,jurisdiction__slug,other_names,description,url,parent__name,classification,contact,address,source_reference
Public Body 76 X,pb-76@76.example.com,bund,,,http://example.com,,Ministry,Some contact stuff,An address,{}""".format(
            source_reference
        )
        imp.import_from_file(BytesIO(csv.encode("utf-8")))
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count, prev_count)

        # Existing entity via slug and georegion identifier
        csv = """name,slug,email,jurisdiction__slug,other_names,description,url,parent__name,classification,contact,address,georegion_identifier
Public Body 76 X,{},pb-76@76.example.com,bund,,,http://example.com,,Ministry,Some contact stuff,An address,{}""".format(
            pb.slug, georegion_identifier
        )
        imp.import_from_file(BytesIO(csv.encode("utf-8")))
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count, prev_count)

        # Add entity if only same slug
        csv = """name,slug,email,jurisdiction__slug,other_names,description,url,parent__name,classification,contact,address
Public Body 76 X,{},pb-76@76.example.com,bund,,,http://example.com,,Ministry,Some contact stuff,An address""".format(
            pb.slug
        )
        imp.import_from_file(BytesIO(csv.encode("utf-8")))
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count, prev_count + 1)

    def test_csv_new_import(self):
        # Make sure classification exist
        ClassificationFactory.create(name="Ministry")
        prev_count = PublicBody.objects.all().count()
        csv = """name,email,jurisdiction__slug,other_names,description,url,parent__name,classification,contact,address,website_dump,request_note
Public Body X 76,pb-76@76.example.com,bund,,,http://example.com,,Ministry,Some contact stuff,An address,,"""
        imp = CSVImporter()
        imp.import_from_file(BytesIO(csv.encode("utf-8")))
        now_count = PublicBody.objects.all().count()
        self.assertEqual(now_count - 1, prev_count)

    def test_csv_command(self):
        from django.core.management import call_command

        csv_file = tempfile.NamedTemporaryFile()
        csv_file.write(
            export_csv_bytes(PublicBody.export_csv(PublicBody.objects.all()))
        )
        csv_file.flush()
        with open(os.devnull, "a") as f:
            call_command("import_csv", csv_file.name, stdout=f)

        csv_file.close()

    def test_csv_import_request(self):
        url = reverse("admin:publicbody-publicbody-import_csv")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/?next=", response.url)

        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/?next=", response.url)

        self.client.logout()
        self.client.login(email="superuser@fragdenstaat.de", password="froide")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/publicbody/publicbody/", response.url)

        response = self.client.post(url, {"url": "test"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/publicbody/publicbody/", response.url)

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
        new_juris = JurisdictionFactory.create(name="peculiar", hidden=True)
        response = self.client.get(new_juris.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_show_public_bodies_of_jurisdiction(self):
        juris = Jurisdiction.objects.all()[0]
        response = self.client.get(
            reverse("publicbody-list", kwargs={"jurisdiction": juris.slug})
        )
        self.assertEqual(response.status_code, 200)


class ApiTest(TestCase):
    def setUp(self):
        self.site = make_world()

    def test_list(self):
        response = self.client.get("/api/v1/publicbody/?format=json")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/v1/jurisdiction/?format=json")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/v1/law/?format=json")
        self.assertEqual(response.status_code, 200)

    def test_detail(self):
        pb = PublicBody.objects.all()[0]
        response = self.client.get("/api/v1/publicbody/%d/?format=json" % pb.pk)
        self.assertEqual(response.status_code, 200)

        law = FoiLaw.objects.all()[0]
        response = self.client.get("/api/v1/law/%d/?format=json" % law.pk)
        self.assertEqual(response.status_code, 200)

        jur = Jurisdiction.objects.all()[0]
        response = self.client.get("/api/v1/jurisdiction/%d/?format=json" % jur.pk)
        self.assertEqual(response.status_code, 200)

    def test_search(self):
        response = self.client.get("/api/v1/publicbody/search/?format=json&q=Body")
        self.assertEqual(response.status_code, 200)

    def test_autocomplete(self):
        pb = PublicBody.objects.all()[0]
        rebuild_index()

        response = self.client.get("%s?q=%s" % ("/api/v1/publicbody/search/", pb.name))
        self.assertEqual(response.status_code, 200)
        obj = json.loads(response.content.decode("utf-8"))
        self.assertIn(pb.name, obj["objects"][0]["name"])
        response = self.client.get(
            "%s?query=%s&jurisdiction=non_existant"
            % ("/api/v1/publicbody/search/", pb.name)
        )
        self.assertEqual(response.status_code, 200)
        obj = json.loads(response.content.decode("utf-8"))
        self.assertEqual(obj["objects"], [])


@pytest.mark.django_db
def test_accept_change_proposal():
    pb = PublicBodyFactory.create()
    change_proposal = PublicBodyChangeProposalFactory.create(publicbody=pb)
    change_proposal.categories.set([CategoryFactory.create(), CategoryFactory.create()])
    change_proposal_categories = set(change_proposal.categories.all())
    assert len(change_proposal_categories) == 2
    ok = change_proposal.accept(pb._created_by)
    assert ok
    pb.refresh_from_db()
    assert pb.name == change_proposal.name
    assert pb.fax == change_proposal.fax
    assert pb.address == change_proposal.address
    assert pb.classification_id == change_proposal.classification_id
    assert pb.jurisdiction_id == change_proposal.jurisdiction_id
    assert set(pb.categories.all()) == change_proposal_categories

    with pytest.raises(PublicBodyChangeProposal.DoesNotExist):
        change_proposal.refresh_from_db()
