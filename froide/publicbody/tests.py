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
from froide.georegion.factories import GeoRegionFactory
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
from .models import (
    FoiLaw,
    Jurisdiction,
    PublicBody,
    PublicBodyChangeProposal,
)


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


@pytest.fixture
def publicbody_data(db):
    # Jurisdictions
    berlin = JurisdictionFactory(name="Berlin", slug="berlin")
    hamburg = JurisdictionFactory(name="Hamburg", slug="hamburg")

    # Classifications
    ministry = ClassificationFactory(name="Ministry", slug="ministry")
    agency = ClassificationFactory(name="Agency", slug="agency")

    # Categories
    environment = CategoryFactory(name="Environment", slug="environment")
    traffic = CategoryFactory(name="Traffic", slug="traffic")

    # Regions
    mitte = GeoRegionFactory(name="Mitte", kind="district")
    altona = GeoRegionFactory(name="Altona", kind="district")

    # PublicBodies
    pb1 = PublicBodyFactory(
        name="Umweltministerium Berlin",
        jurisdiction=berlin,
        classification=ministry,
        description="Zuständig für Umweltschutz",
    )
    pb1.categories.add(environment)
    pb1.regions.add(mitte)

    pb2 = PublicBodyFactory(
        name="Verkehrsministerium Berlin",
        jurisdiction=berlin,
        classification=ministry,
        description="Zuständig für Verkehr",
    )
    pb2.categories.add(traffic)

    pb3 = PublicBodyFactory(
        name="Umweltbehörde Hamburg",
        jurisdiction=hamburg,
        classification=agency,
        description="Hamburger Umweltbehörde",
    )
    pb3.categories.add(environment)
    pb3.regions.add(altona)

    pb4 = PublicBodyFactory(
        name="Bezirksamt Mitte",
        jurisdiction=berlin,
        classification=agency,
    )
    pb4.regions.add(mitte)

    rebuild_index()

    yield {
        "jurisdictions": {"berlin": berlin, "hamburg": hamburg},
        "classifications": {"ministry": ministry, "agency": agency},
        "categories": {"environment": environment, "traffic": traffic},
        "regions": {"mitte": mitte, "altona": altona},
        "publicbodies": {"pb1": pb1, "pb2": pb2, "pb3": pb3, "pb4": pb4},
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query_params,expected_count,expected_names",
    [
        # Text search
        ({"q": "Umwelt"}, 2, ["Umweltministerium Berlin", "Umweltbehörde Hamburg"]),
        # Jurisdiction filter
        (
            {"jurisdiction": "berlin"},
            3,
            [
                "Umweltministerium Berlin",
                "Verkehrsministerium Berlin",
                "Bezirksamt Mitte",
            ],
        ),
        # Classification filter
        (
            {"classification": "ministry"},
            2,
            ["Umweltministerium Berlin", "Verkehrsministerium Berlin"],
        ),
        # Category filter
        (
            {"categories": "environment"},
            2,
            ["Umweltministerium Berlin", "Umweltbehörde Hamburg"],
        ),
        # GeoRegion filter
        ({"regions": "mitte"}, 2, ["Umweltministerium Berlin", "Bezirksamt Mitte"]),
        # GeoRegion kind filter
        (
            {"regions_kind": "district"},
            3,
            ["Umweltministerium Berlin", "Bezirksamt Mitte", "Umweltbehörde Hamburg"],
        ),
        # Combination text + jurisdiction
        ({"q": "Umwelt", "jurisdiction": "berlin"}, 1, ["Umweltministerium Berlin"]),
        # Combination jurisdiction + classification
        (
            {"jurisdiction": "berlin", "classification": "ministry"},
            2,
            ["Umweltministerium Berlin", "Verkehrsministerium Berlin"],
        ),
        # Combination category + classification
        (
            {"categories": "environment", "classification": "ministry"},
            1,
            ["Umweltministerium Berlin"],
        ),
        # No results
        ({"q": "NichtVorhanden"}, 0, []),
        # Empty search (all results)
        (
            {},
            4,
            [
                "Umweltministerium Berlin",
                "Verkehrsministerium Berlin",
                "Umweltbehörde Hamburg",
                "Bezirksamt Mitte",
            ],
        ),
    ],
    ids=[
        "text_search",
        "jurisdiction_filter",
        "classification_filter",
        "category_filter",
        "georegion_filter",
        "georegion_kind_filter",
        "text_and_jurisdiction",
        "jurisdiction_and_classification",
        "category_and_classification",
        "no_results",
        "empty_search",
    ],
)
def test_publicbody_search_filters(
    client, publicbody_data, query_params, expected_count, expected_names
):
    """Test different combinations of search and filters for the publicbody search API."""

    test_params = query_params.copy()

    # Replace slugs with actual IDs.
    if "jurisdiction" in test_params:
        slug = test_params["jurisdiction"]
        test_params["jurisdiction"] = publicbody_data["jurisdictions"][slug].pk

    if "classification" in test_params:
        slug = test_params["classification"]
        test_params["classification"] = publicbody_data["classifications"][slug].pk

    if "categories" in test_params:
        slug = test_params["categories"]
        test_params["categories"] = publicbody_data["categories"][slug].pk

    if "regions" in test_params:
        slug = test_params["regions"]
        test_params["regions"] = publicbody_data["regions"][slug].pk

    url = reverse("api:publicbody-search")
    response = client.get(url, test_params)

    assert response.status_code == 200
    data = response.json()

    # Check counts.
    assert len(data["objects"]) == expected_count
    assert data["meta"]["total_count"] == expected_count

    # Check names.
    result_names = {pb["name"] for pb in data["objects"]}
    assert result_names == set(expected_names)

    # Check facets.
    assert "facets" in data
    facets = data["facets"]["fields"]
    assert "jurisdiction" in facets
    assert "classification" in facets
    assert "categories" in facets
    assert "regions" in facets


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
