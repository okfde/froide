from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

import pytest

from froide.account.factories import UserFactory

from ..factories import (
    CategoryFactory,
    JurisdictionFactory,
    PublicBodyChangeProposalFactory,
    PublicBodyFactory,
)
from ..models import (
    ProposedPublicBody,
    ProposedPublicBodyContact,
    PublicBody,
    PublicBodyChangeProposal,
    PublicBodyContact,
)


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


@pytest.mark.django_db
def test_new_publicbody_proposal(client, dummy_user):
    jurisdiction = JurisdictionFactory.create(name="TestJuris")
    existing_publicbody = PublicBodyFactory.create(
        name="TestPB", jurisdiction=jurisdiction
    )
    propose_url = reverse("publicbody-propose")
    response = client.get(propose_url)
    assert response.status_code == 302
    client.force_login(dummy_user)
    response = client.get(propose_url)
    assert response.status_code == 200
    data = {
        "name": existing_publicbody.name,
        "reason": "I want to add this public body",
        "email": "pb@example.com",
        "url": "http://example.com",
        "address": "An address",
        "jurisdiction": jurisdiction.pk,
        "contacts-TOTAL_FORMS": "0",
        "contacts-INITIAL_FORMS": "0",
    }
    response = client.post(propose_url, data)
    assert response.status_code == 200
    # Name already exists
    assert "name" in response.context["form"].errors

    data["name"] = "New Public Body"
    response = client.post(propose_url, data)
    assert response.status_code == 302

    proposed = ProposedPublicBody.objects.get(name=data["name"])
    assert response.url == proposed.get_absolute_url()

    assert proposed.reason == data["reason"]
    assert proposed.email == data["email"]
    assert proposed.url == data["url"]
    assert proposed.address == data["address"]
    assert proposed.jurisdiction_id == data["jurisdiction"]


@pytest.mark.django_db
def test_new_publicbody_proposal_extra_contact(client, dummy_user):
    jurisdiction = JurisdictionFactory.create(name="TestJuris")
    category = CategoryFactory.create(name="TestCategory")
    propose_url = reverse("publicbody-propose")
    client.force_login(dummy_user)
    data = {
        "name": "New Public Body",
        "reason": "I want to add this public body",
        "email": "pb@example.com",
        "url": "http://example.com",
        "address": "An address",
        "jurisdiction": jurisdiction.pk,
        "contacts-TOTAL_FORMS": "1",
        "contacts-INITIAL_FORMS": "0",
        "contacts-0-id": "",
        "contacts-0-publicbody": "",
        "contacts-0-email": "contact@example.com",
        "contacts-0-category": category.pk,
    }
    response = client.get(propose_url)
    assert b"contacts-TOTAL_FORMS" in response.content
    assert b"contacts-0-publicbody" in response.content

    response = client.post(propose_url, data)

    assert response.status_code == 302
    proposed = ProposedPublicBody.objects.get(name=data["name"])
    assert response.url == proposed.get_absolute_url()

    assert proposed.reason == data["reason"]
    assert proposed.email == data["email"]
    assert proposed.url == data["url"]
    assert proposed.address == data["address"]
    assert proposed.jurisdiction_id == data["jurisdiction"]

    contact = ProposedPublicBodyContact.objects.get(publicbody=proposed)
    assert contact.email == data["contacts-0-email"]
    assert contact.category_id == data["contacts-0-category"]
    assert contact.confirmed is False


@pytest.mark.django_db
def test_add_new_proposal_extra_contact(client, dummy_user):
    publicbody = PublicBodyFactory.create(name="TestPB")
    category = CategoryFactory.create(name="TestCategory")
    category2 = CategoryFactory.create(name="TestCategory2")
    category3 = CategoryFactory.create(name="TestCategory3")
    change_url = reverse("publicbody-change", kwargs={"pk": publicbody.pk})
    client.force_login(dummy_user)
    data = {
        "name": publicbody.name,
        "reason": "I want to add this public body",
        "email": publicbody.email,
        "url": publicbody.url,
        "address": publicbody.address,
        "jurisdiction": publicbody.jurisdiction_id,
        "contacts-TOTAL_FORMS": "2",
        "contacts-INITIAL_FORMS": "0",
        "contacts-0-id": "",
        "contacts-0-publicbody": publicbody.id,
        "contacts-0-email": "contact@example.com",
        "contacts-0-category": category.pk,
        "contacts-1-id": "",
        "contacts-1-publicbody": publicbody.id,
        "contacts-1-email": "contact2@example.com",
        "contacts-1-category": category.pk,
    }
    response = client.get(change_url)
    assert response.status_code == 200

    response = client.post(change_url, data)
    assert response.status_code == 200
    # Two identical contacts are not allowed, so there should be a form error
    assert len(response.context["contact_formset"].non_form_errors()) == 1

    data["contacts-1-category"] = category2.pk
    response = client.post(change_url, data)
    assert response.status_code == 302
    proposed_change = PublicBodyChangeProposal.objects.get(
        publicbody=publicbody, reason=data["reason"]
    )
    assert response.url == publicbody.get_absolute_url()

    assert proposed_change.reason == data["reason"]
    assert proposed_change.email == data["email"]
    assert proposed_change.url == data["url"]
    assert proposed_change.address == data["address"]
    assert proposed_change.jurisdiction_id == data["jurisdiction"]

    contact = ProposedPublicBodyContact.objects.get(
        publicbody=publicbody, category=category
    )
    assert contact.email == data["contacts-0-email"]
    assert contact.category_id == data["contacts-0-category"]
    assert contact.confirmed is False
    assert contact.user == dummy_user

    contact = ProposedPublicBodyContact.objects.get(
        publicbody=publicbody, category=category2
    )
    assert contact.email == data["contacts-1-email"]
    assert contact.category_id == data["contacts-1-category"]
    assert contact.confirmed is False
    assert contact.user == dummy_user

    PublicBodyContact.objects.create(
        publicbody=publicbody,
        category=category3,
        email="other-user-unconfirmed@example.com",
        confirmed=False,
    )
    PublicBodyContact.objects.create(
        publicbody=publicbody, category=category, email="double-category@example.com"
    )
    response = client.get(change_url)
    assert response.status_code == 200
    assert b"other-user-unconfirmed@example.com" not in response.content
    assert b"double-category@example.com" in response.content
    assert b"contact@example.com" in response.content
    assert b"contact2@example.com" in response.content


@pytest.mark.django_db
def test_accept_new_proposal_extra_contact(client, dummy_user):
    some_user = UserFactory.create(username="someuser")
    publicbody = PublicBodyFactory.create(name="TestPB")
    category = CategoryFactory.create(name="TestCategory")
    category2 = CategoryFactory.create(name="TestCategory2")
    contact = PublicBodyContact.objects.create(
        publicbody=publicbody,
        category=category,
        user=some_user,
        email="other-user-unconfirmed@example.com",
        confirmed=False,
    )
    accept_url = reverse("publicbody-accept", kwargs={"pk": publicbody.pk})
    client.force_login(dummy_user)
    response = client.get(accept_url)
    assert response.status_code == 404

    ct = ContentType.objects.get_for_model(PublicBody)
    perm = Permission.objects.get(content_type=ct, codename="moderate")
    dummy_user.user_permissions.add(perm)
    client.force_login(dummy_user)

    response = client.get(accept_url)
    assert response.status_code == 200

    data = {
        "name": publicbody.name,
        "reason": "I want to change this public body",
        "email": publicbody.email,
        "url": publicbody.url,
        "address": publicbody.address,
        "jurisdiction": publicbody.jurisdiction_id,
        "contacts-TOTAL_FORMS": "2",
        "contacts-INITIAL_FORMS": "1",
        "contacts-0-id": contact.id,
        "contacts-0-publicbody": publicbody.id,
        "contacts-0-email": contact.email,
        "contacts-0-category": contact.category_id,
        "contacts-1-id": "",
        "contacts-1-publicbody": publicbody.id,
        "contacts-1-email": "contact2@example.com",
        "contacts-1-category": category2.pk,
    }
    response = client.post(accept_url, data)
    assert response.status_code == 302

    contact = PublicBodyContact.objects.get(publicbody=publicbody, category=category)
    assert contact.email == data["contacts-0-email"]
    assert contact.category_id == data["contacts-0-category"]
    assert contact.confirmed is True
    assert contact.user == dummy_user

    contact = PublicBodyContact.objects.get(publicbody=publicbody, category=category2)
    assert contact.email == data["contacts-1-email"]
    assert contact.category_id == data["contacts-1-category"]
    assert contact.confirmed is True
    assert contact.user == dummy_user
