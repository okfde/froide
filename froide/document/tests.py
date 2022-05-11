from django.test import TestCase
from django.urls import reverse

import factory

from froide.foirequest.tests import factories
from froide.helper.text_utils import slugify
from froide.team.models import TeamMembership
from froide.team.tests import TeamFactory, TeamMembershipFactory

from .models import Document, DocumentCollection


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Document

    title = factory.Sequence(lambda n: "Document {}".format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.title))
    team = factory.SubFactory(TeamFactory)


class DocumentCollectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentCollection

    title = factory.Sequence(lambda n: "DocumentCollection {}".format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.title))
    user = factory.SubFactory(factories.UserFactory)
    team = factory.SubFactory(TeamFactory)


class DocumentAccessTest(TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create()

        self.owner_team = TeamFactory.create()
        TeamMembershipFactory.create(
            user=self.user, team=self.owner_team, role=TeamMembership.ROLE.OWNER
        )

    def test_unlisted_document_needs_slug(self):
        doc = DocumentFactory.create(user=self.user, public=True, listed=False)

        url = reverse(
            "filingcabinet:document-detail_short",
            kwargs={
                "pk": doc.pk,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        url = reverse(
            "filingcabinet:document-detail", kwargs={"pk": doc.pk, "slug": doc.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.user)
        url = reverse(
            "filingcabinet:document-detail_short",
            kwargs={
                "pk": doc.pk,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_list_unlisted_document_api(self):
        DocumentFactory.create(user=self.user, public=True, listed=False)
        url = reverse("api:document-list")
        response = self.client.get(url)
        self.assertEqual(response.json()["meta"]["total_count"], 0)
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.json()["meta"]["total_count"], 1)

    def test_retrieve_unlisted_document_api(self):
        doc = DocumentFactory.create(user=self.user, public=True, listed=False)
        url = reverse("api:document-detail", kwargs={"pk": doc.pk})
        response = self.client.get(url)

        url = reverse("api:document-detail", kwargs={"pk": doc.pk})
        response = self.client.get(url + "?uid=" + str(doc.uid))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_unlisted_documentcollection_needs_slug(self):
        collection = DocumentCollectionFactory.create(
            user=self.user, public=True, listed=False
        )

        url = reverse(
            "filingcabinet:document-collection_short",
            kwargs={
                "pk": collection.pk,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        url = reverse(
            "filingcabinet:document-collection",
            kwargs={"pk": collection.pk, "slug": collection.slug},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.user)
        url = reverse(
            "filingcabinet:document-collection_short",
            kwargs={
                "pk": collection.pk,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_list_unlisted_documentcollection_api(self):
        DocumentCollectionFactory.create(user=self.user, public=True, listed=False)
        url = reverse("api:documentcollection-list")
        response = self.client.get(url)
        self.assertEqual(response.json()["meta"]["total_count"], 0)
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.json()["meta"]["total_count"], 1)

    def test_retrieve_unlisted_documentcollection_api(self):
        collection = DocumentCollectionFactory.create(
            user=self.user, public=True, listed=False
        )
        url = reverse("api:documentcollection-detail", kwargs={"pk": collection.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

        response = self.client.get(url + "?uid=" + str(collection.uid))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def assertForbidden(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account-login"), response["Location"])
        self.assertIn("?next=", response["Location"])

    def test_set_title(self):
        document = DocumentFactory.create(
            team=self.owner_team, public=True, listed=False
        )

        self.client.logout()
        url = reverse("document-set_title", kwargs={"pk": document.pk})
        response = self.client.post(url, data={"title": "MARKER"})
        self.assertForbidden(response)

        self.client.force_login(self.user)
        url = reverse("document-set_title", kwargs={"pk": document.pk})
        response = self.client.post(url, data={"title": "MARKER"})
        self.assertEqual(response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.title, "MARKER")

        url = reverse("document-set_title", kwargs={"pk": document.pk})
        response = self.client.post(
            url, data={"description": "MARKER"}
        )  # Wrong form field
        self.assertEqual(response.status_code, 400)

    def test_set_description(self):
        document = DocumentFactory.create(
            team=self.owner_team, public=True, listed=False
        )

        self.client.logout()
        url = reverse(
            "document-set_description",
            kwargs={"pk": document.pk},
        )
        response = self.client.post(url, data={"description": "MARKER"})
        self.assertForbidden(response)

        self.client.force_login(self.user)
        url = reverse(
            "document-set_description",
            kwargs={"pk": document.pk},
        )
        response = self.client.post(url, data={"description": "MARKER"})
        self.assertEqual(response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.description, "MARKER")
