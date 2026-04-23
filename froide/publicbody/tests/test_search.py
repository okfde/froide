from django.urls import reverse

import pytest

from froide.foirequest.tests.factories import rebuild_index
from froide.georegion.factories import GeoRegionFactory
from froide.helper.search.signal_processor import realtime_search

from ..factories import (
    CategoryFactory,
    ClassificationFactory,
    JurisdictionFactory,
    PublicBodyFactory,
)


@pytest.fixture
def publicbody_data(db):
    # Jurisdictions
    berlin = JurisdictionFactory(name="Berlin", slug="berlin")
    hamburg = JurisdictionFactory(name="Hamburg", slug="hamburg")

    # Classifications
    ministry = ClassificationFactory(name="Ministry", slug="ministry")
    agency = ClassificationFactory(name="Agency", slug="agency")

    # Categories
    environment = CategoryFactory(name="Environment", slug="environment", is_topic=True)
    traffic = CategoryFactory(name="Traffic", slug="traffic", is_topic=True)

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


@pytest.mark.xdist_group(name="sequential")
class TestPublicBodyView:
    """Tests for the publicbody list view and its search/filter functionality."""

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "query_params,expected_names",
        [
            # No filters — all results
            (
                {},
                [
                    "Umweltministerium Berlin",
                    "Verkehrsministerium Berlin",
                    "Umweltbehörde Hamburg",
                    "Bezirksamt Mitte",
                ],
            ),
            # Text search
            ({"q": "Umwelt"}, ["Umweltministerium Berlin", "Umweltbehörde Hamburg"]),
            # Jurisdiction filter
            (
                {"jurisdiction": "berlin"},
                [
                    "Umweltministerium Berlin",
                    "Verkehrsministerium Berlin",
                    "Bezirksamt Mitte",
                ],
            ),
            # Category filter
            (
                {"category": "environment"},
                ["Umweltministerium Berlin", "Umweltbehörde Hamburg"],
            ),
            # Classification filter
            (
                {"classification": "ministry"},
                ["Umweltministerium Berlin", "Verkehrsministerium Berlin"],
            ),
            # Combination: jurisdiction + text search
            ({"jurisdiction": "berlin", "q": "Umwelt"}, ["Umweltministerium Berlin"]),
            # Combination: jurisdiction + classification
            (
                {"jurisdiction": "berlin", "classification": "ministry"},
                ["Umweltministerium Berlin", "Verkehrsministerium Berlin"],
            ),
            # No results
            ({"q": "NichtVorhanden"}, []),
            # Empty search (all results)
            (
                {},
                [
                    "Umweltministerium Berlin",
                    "Verkehrsministerium Berlin",
                    "Umweltbehörde Hamburg",
                    "Bezirksamt Mitte",
                ],
            ),
        ],
        ids=[
            "no_filters",
            "text_search",
            "jurisdiction_filter",
            "category_filter",
            "classification_filter",
            "jurisdiction_and_text",
            "jurisdiction_and_classification",
            "no_results",
            "empty_search",
        ],
    )
    def test_search_filters(
        self, client, publicbody_data, query_params, expected_names
    ):
        """Test that the PublicBody list view applies search filters correctly."""

        url = reverse("publicbody-list")
        response = client.get(url, query_params)

        assert response.status_code == 200

        result_names = {obj.name for obj in response.context["object_list"]}
        assert result_names == set(expected_names)


@pytest.mark.xdist_group(name="sequential")
class TestPublicBodySearchAPI:
    """Tests for the publicbody search API.

    Note: The search endpoint also serves as the autocomplete backend for the
    frontend's publicbody chooser components (see pb-chooser-mixin.js).
    A separate /autocomplete/ endpoint exists but is unused for publicbodies.
    """

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "query_params,expected_names",
        [
            # Text search
            ({"q": "Umwelt"}, ["Umweltministerium Berlin", "Umweltbehörde Hamburg"]),
            # Jurisdiction filter
            (
                {"jurisdiction": "berlin"},
                [
                    "Umweltministerium Berlin",
                    "Verkehrsministerium Berlin",
                    "Bezirksamt Mitte",
                ],
            ),
            # Classification filter
            (
                {"classification": "ministry"},
                ["Umweltministerium Berlin", "Verkehrsministerium Berlin"],
            ),
            # Category filter
            (
                {"categories": "environment"},
                ["Umweltministerium Berlin", "Umweltbehörde Hamburg"],
            ),
            # GeoRegion filter
            ({"regions": "mitte"}, ["Umweltministerium Berlin", "Bezirksamt Mitte"]),
            # GeoRegion kind filter
            (
                {"regions_kind": "district"},
                [
                    "Umweltministerium Berlin",
                    "Bezirksamt Mitte",
                    "Umweltbehörde Hamburg",
                ],
            ),
            # Combination text + jurisdiction
            ({"q": "Umwelt", "jurisdiction": "berlin"}, ["Umweltministerium Berlin"]),
            # Combination jurisdiction + classification
            (
                {"jurisdiction": "berlin", "classification": "ministry"},
                ["Umweltministerium Berlin", "Verkehrsministerium Berlin"],
            ),
            # Combination category + classification
            (
                {"categories": "environment", "classification": "ministry"},
                ["Umweltministerium Berlin"],
            ),
            # No results
            ({"q": "NichtVorhanden"}, []),
            # Empty search (all results)
            (
                {},
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
    def test_search_filters(
        self, client, publicbody_data, query_params, expected_names
    ):
        """Test different combinations of search and filters."""

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
        assert len(data["objects"]) == len(expected_names)
        assert data["meta"]["total_count"] == len(expected_names)

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
    @pytest.mark.parametrize(
        "api_params",
        [
            {"jurisdiction": "invalid"},
            {"jurisdiction": 0},
            {"classification": "invalid"},
            {"classification": 0},
            {"categories": "invalid"},
            {"categories": 0},
            {"regions": "invalid"},
            {"regions": 0},
            {"regions_kind": "invalid"},
        ],
        ids=[
            "invalid_jurisdiction_string",
            "nonexistent_jurisdiction_id",
            "invalid_classification_string",
            "nonexistent_classification_id",
            "invalid_categories_string",
            "nonexistent_categories_id",
            "invalid_regions_string",
            "nonexistent_regions_id",
            "nonexistent_regions_kind",
        ],
    )
    def test_invalid_input(self, client, publicbody_data, api_params):
        """Invalid filter values should return 400."""
        url = reverse("api:publicbody-search")
        response = client.get(url, api_params)

        assert response.status_code == 400

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "params",
        [
            {"q": "Umwelt"},
            {"jurisdiction": "berlin"},
            {"category": "environment"},
            {"classification": "ministry"},
            {"q": "Umwelt", "jurisdiction": "berlin"},
        ],
        ids=[
            "text_search",
            "jurisdiction",
            "category",
            "classification",
            "text_and_jurisdiction",
        ],
    )
    def test_api_and_view_return_same_results(self, client, publicbody_data, params):
        """API and view should return the same set of results for equivalent queries."""

        # Build API params: replace slugs with PKs and rename category -> categories
        api_params = {}
        slug_to_pk = {
            "jurisdiction": "jurisdictions",
            "classification": "classifications",
            "category": "categories",
        }
        for key, value in params.items():
            api_key = "categories" if key == "category" else key
            if key in slug_to_pk:
                api_params[api_key] = publicbody_data[slug_to_pk[key]][value].pk
            else:
                api_params[api_key] = value

        api_url = reverse("api:publicbody-search")
        api_response = client.get(api_url, api_params)
        assert api_response.status_code == 200
        api_names = {pb["name"] for pb in api_response.json()["objects"]}

        view_url = reverse("publicbody-list")
        view_response = client.get(view_url, params)
        assert view_response.status_code == 200
        view_names = {obj.name for obj in view_response.context["object_list"]}

        assert api_names == view_names


@pytest.mark.django_db(transaction=True)
@pytest.mark.xdist_group(name="sequential")
def test_proposals_not_in_search(world, client):
    rebuild_index()

    api_url = reverse("api:publicbody-search")

    # make sure proposed public bodies are not indexed and returned in search api
    with realtime_search():
        pb_proposal = PublicBodyFactory.create(name="Indextest-1", confirmed=False)
        pb_confirmed = PublicBodyFactory.create(name="Indextest-2", confirmed=True)

    api_response = client.get(api_url, {"q": "Indextest"})
    assert api_response.status_code == 200
    data = api_response.json()
    assert len(data["objects"]) == 1
    assert data["objects"][0]["id"] == pb_confirmed.id

    # confirming a proposal should make it appear in the index via the save signal
    with realtime_search():
        pb_proposal.confirmed = True
        pb_proposal.save()

    api_response = client.get(api_url, {"q": "Indextest"})
    assert api_response.status_code == 200
    data = api_response.json()
    result_ids = {obj["id"] for obj in data["objects"]}
    assert result_ids == {pb_proposal.id, pb_confirmed.id}
