from django.test import Client
from django.urls import reverse

import pytest

from froide.foirequest.tests import factories


@pytest.mark.django_db
def test_message_draft(client: Client, user):
    request = factories.FoiRequestFactory.create(user=user)
    ok = client.login(email=user.email, password="froide")
    assert ok

    # can't create an email
    response = client.post(
        "/api/v1/message/draft/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "kind": "email",
        },
        content_type="application/json",
    )
    assert response.status_code == 400

    # must use draft endpoint
    response = client.post(
        "/api/v1/message/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 405

    # create message draft
    response = client.post(
        "/api/v1/message/draft/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    assert "/draft/" in response.json()["resource_uri"]

    message_id = response.json()["id"]
    resource_uri = reverse("api:message-draft-detail", kwargs={"pk": message_id})

    response = client.patch(
        resource_uri, data={"status": "resolved"}, content_type="application/json"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"

    response = client.delete(resource_uri)
    assert response.status_code == 204

    # create message draft
    response = client.post(
        "/api/v1/message/draft/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    message_id = response.json()["id"]
    resource_uri = reverse("api:message-draft-detail", kwargs={"pk": message_id})

    # can't set sent stauts
    assert response.json()["sent"] is True
    response = client.patch(
        resource_uri, data={"sent": False}, content_type="application/json"
    )
    assert response.json()["sent"] is True

    # doesn't appear in regular messages
    response = client.get(reverse("api:message-detail", kwargs={"pk": message_id}))
    assert response.status_code == 404

    # publish
    resource_uri = reverse("api:message-draft-publish", kwargs={"pk": message_id})
    response = client.post(resource_uri)
    assert response.status_code == 200
    assert "/draft/" not in response.json()["resource_uri"]

    # can't delete anymore
    resource_uri = reverse("api:message-detail", kwargs={"pk": message_id})
    response = client.delete(resource_uri)
    assert response.status_code == 405

    resource_uri = reverse("api:message-draft-detail", kwargs={"pk": message_id})
    response = client.delete(resource_uri)
    assert response.status_code == 404


@pytest.mark.django_db
def test_auth(client, user):
    user2 = factories.UserFactory.create()
    request = factories.FoiRequestFactory.create(user=user2)

    # need to be logged in
    client.logout()
    response = client.post(
        "/api/v1/message/draft/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 401

    # needs to be own request
    client.login(email=user.email, password="froide")
    response = client.post(
        "/api/v1/message/draft/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 400

    # create message draft
    request2 = factories.FoiRequestFactory.create(user=user)
    response = client.post(
        "/api/v1/message/draft/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request2.pk}),
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    # can't change it to other's people request
    response = client.patch(
        response.json()["resource_uri"],
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
        },
        content_type="application/json",
    )
    assert response.status_code == 400
