from django.test import Client
from django.urls import reverse

import pytest

from froide.foirequest.models.event import FoiEvent
from froide.foirequest.tests import factories


@pytest.mark.django_db
def test_message(client: Client, user):
    assert client.login(email=user.email, password="froide")

    request = factories.FoiRequestFactory.create(user=user)
    other_request = factories.FoiRequestFactory.create()
    message = factories.FoiMessageFactory.create(request=request)

    # can't create a message
    response = client.post(
        reverse("api:message-list"),
        data={
            "request": reverse("api:request-detail", kwargs={"pk": 1}),
            "kind": "email",
        },
        content_type="application/json",
    )
    assert response.status_code == 405

    timestamp = "2000-01-01T12:00:00+01:00"

    # can only update some fields
    response = client.patch(
        reverse("api:message-detail", kwargs={"pk": message.pk}),
        data={
            "sent": False,
            "kind": "post",
            "request": reverse("api:request-detail", kwargs={"pk": other_request.pk}),
            "timestamp": timestamp,
            "is_draft": True,
            "not_publishable": True,
        },
        content_type="application/json",
    )
    data = response.json()
    assert data["sent"]
    assert data["kind"] == "email"
    assert reverse("api:request-detail", kwargs={"pk": request.pk}) in data["request"]
    assert data["timestamp"] != timestamp
    assert not data["is_draft"]
    assert not data["not_publishable"]

    # can update some fields
    response = client.patch(
        reverse("api:message-detail", kwargs={"pk": message.pk}),
        data={
            "registered_mail_date": timestamp,
        },
        content_type="application/json",
    )
    data = response.json()
    assert response.status_code == 200
    assert "2000-01-01" in data["registered_mail_date"]

    # can't delete
    response = client.delete(reverse("api:message-detail", kwargs={"pk": message.pk}))
    assert response.status_code == 405


@pytest.mark.django_db
def test_message_draft(client: Client, user):
    request = factories.FoiRequestFactory.create(user=user)
    assert client.login(email=user.email, password="froide")

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
    data = {
        "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
        "kind": "post",
        "is_response": True,
        "sender_public_body": reverse(
            "api:publicbody-detail", kwargs={"pk": request.public_body.pk}
        ),
    }

    response = client.post(
        "/api/v1/message/draft/",
        data=data,
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
        data=data,
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

    # appears in drafts list
    response = client.get(reverse("api:message-draft-list"))
    assert response.status_code == 200
    assert resource_uri in str(response.content)

    # appears in filtered drafts list
    response = client.get(reverse("api:message-draft-list") + f"?request={request.pk}")
    assert response.status_code == 200
    assert resource_uri in str(response.content)

    # user send a message to public body
    public_body = factories.PublicBodyFactory()
    request_data = {
        "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
        "kind": "post",
        "recipient_public_body": reverse(
            "api:publicbody-detail", kwargs={"pk": public_body.pk}
        ),
        "sender_public_body": None,
        "is_response": False,
    }
    response = client.post(
        "/api/v1/message/draft/",
        data=request_data,
        content_type="application/json",
    )
    data = response.json()
    assert response.status_code == 201
    assert reverse("api:request-detail", kwargs={"pk": request.pk}) in data["request"]

    message_id = response.json()["id"]
    publish_uri = reverse("api:message-draft-publish", kwargs={"pk": message_id})

    response = client.post(publish_uri)
    assert response.status_code == 200
    data = response.json()

    # check date is correct
    assert "12:00:00" in data["timestamp"]

    # ensure event was created
    assert FoiEvent.objects.get(
        message=message_id, event_name="message_sent", user=user
    )

    # can't delete anymore
    resource_uri = reverse("api:message-detail", kwargs={"pk": message_id})
    response = client.delete(resource_uri)
    assert response.status_code == 405

    resource_uri = reverse("api:message-draft-detail", kwargs={"pk": message_id})
    response = client.delete(resource_uri)
    assert response.status_code == 404

    # create + publish another message draft
    response = client.post(
        "/api/v1/message/draft/",
        data=request_data,
        content_type="application/json",
    )
    assert response.status_code == 201

    message_id = response.json()["id"]
    publish_uri = reverse("api:message-draft-publish", kwargs={"pk": message_id})

    response = client.post(publish_uri)
    assert response.status_code == 200
    data = response.json()

    # check date is correct - one second after the other one!
    assert "12:00:01" in data["timestamp"]


@pytest.mark.django_db
def test_draft_auth(client, user):
    user2 = factories.UserFactory.create()
    request = factories.FoiRequestFactory.create(user=user2)

    data = {
        "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
        "kind": "post",
        "is_response": True,
        "sender_public_body": reverse(
            "api:publicbody-detail", kwargs={"pk": request.public_body.pk}
        ),
    }

    # need to be logged in
    client.logout()
    response = client.post(
        "/api/v1/message/draft/",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 401

    # can't publish drafts
    draft = factories.FoiMessageDraftFactory.create(request=request)
    response = client.post(
        reverse("api:message-draft-publish", kwargs={"pk": draft.pk})
    )
    assert response.status_code == 401

    # needs to be own request
    client.login(email=user.email, password="froide")
    response = client.post(
        "/api/v1/message/draft/",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 400

    # create message draft
    request2 = factories.FoiRequestFactory.create(user=user)
    data = {
        "request": reverse("api:request-detail", kwargs={"pk": request2.pk}),
        "kind": "post",
        "is_response": True,
        "sender_public_body": reverse(
            "api:publicbody-detail", kwargs={"pk": request2.public_body.pk}
        ),
    }

    response = client.post(
        "/api/v1/message/draft/",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 201
    resource_uri = response.json()["resource_uri"]

    # can't change it to other's people request
    response = client.patch(
        resource_uri,
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
        },
        content_type="application/json",
    )
    assert response.status_code == 400

    # drafts can't be seen by others
    client.logout()
    response = client.get(resource_uri)
    assert response.status_code == 401

    client.login(email=user2.email, password="froide")
    response = client.get(resource_uri)
    assert response.status_code == 404
