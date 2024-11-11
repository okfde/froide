import json

from django.test import Client
from django.urls import reverse

import pytest

from froide.foirequest.tests import factories


@pytest.mark.django_db
def test_message_draft(client: Client, user):
    request = factories.FoiRequestFactory.create(user=user)
    ok = client.login(email=user.email, password="froide")
    assert ok

    # must specify kind
    response = client.post(
        "/api/v1/message/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "is_draft": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 400

    # can't create an email
    response = client.post(
        "/api/v1/message/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "is_draft": True,
            "kind": "email",
        },
        content_type="application/json",
    )
    assert response.status_code == 400

    # create message draft
    response = client.post(
        "/api/v1/message/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "is_draft": True,
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    message_id = json.loads(response.content)["id"]
    resource_uri = reverse("api:message-detail", kwargs={"pk": message_id})

    response = client.patch(
        resource_uri, data={"status": "resolved"}, content_type="application/json"
    )
    data = json.loads(response.content)
    assert response.status_code == 200
    assert data["status"] == "resolved"

    response = client.delete(resource_uri)
    assert response.status_code == 204


@pytest.mark.django_db
def test_message_not_editable(client: Client, user):
    ok = client.login(email=user.email, password="froide")
    assert ok
    request = factories.FoiRequestFactory.create(user=user)

    # not a draft
    response = client.post(
        "/api/v1/message/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    message_id = json.loads(response.content)["id"]
    resource_uri = reverse("api:message-detail", kwargs={"pk": message_id})

    response = client.delete(resource_uri)
    assert response.status_code == 403

    # first draft, then not
    response = client.post(
        "/api/v1/message/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "is_draft": True,
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    message_id = json.loads(response.content)["id"]
    resource_uri = reverse("api:message-detail", kwargs={"pk": message_id})

    response = client.patch(
        resource_uri, data={"is_draft": False}, content_type="application/json"
    )
    assert response.status_code == 200

    response = client.delete(resource_uri)
    assert response.status_code == 403


@pytest.mark.django_db
def test_auth(client, user):
    user2 = factories.UserFactory.create()
    request = factories.FoiRequestFactory.create(user=user2)

    # need to be logged in
    client.logout()
    response = client.post(
        "/api/v1/message/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "is_draft": True,
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 401

    # needs to be own request
    client.login(email=user.email, password="froide")
    response = client.post(
        "/api/v1/message/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "is_draft": True,
            "kind": "post",
        },
        content_type="application/json",
    )
    assert response.status_code == 400
