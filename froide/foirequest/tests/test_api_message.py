from django.test import Client
from django.urls import reverse

import pytest

from froide.foirequest.models.event import FoiEvent
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

    # appears in drafts list
    response = client.get(reverse("api:message-draft-list"))
    assert response.status_code == 200
    assert resource_uri in str(response.content)

    # appears in filtered drafts list
    response = client.get(reverse("api:message-draft-list") + f"?request={request.pk}")
    assert response.status_code == 200
    assert resource_uri in str(response.content)

    # can't publish without recipient
    publish_uri = reverse("api:message-draft-publish", kwargs={"pk": message_id})
    response = client.post(publish_uri)
    assert response.status_code == 400

    # letter was sent by public body to user
    public_body = factories.PublicBodyFactory.create()
    response = client.patch(
        resource_uri,
        data={
            "sender_public_body": reverse(
                "api:publicbody-detail", kwargs={"pk": public_body.pk}
            ),
            "recipient_public_body": None,
            "is_response": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 200

    # publish
    response = client.post(publish_uri)
    assert response.status_code == 200
    assert "/draft/" not in response.json()["resource_uri"]

    # ensure event was created
    assert FoiEvent.objects.get(
        message=response.json()["id"], event_name="message_received", user=user
    )

    # can't delete anymore
    resource_uri = reverse("api:message-detail", kwargs={"pk": message_id})
    response = client.delete(resource_uri)
    assert response.status_code == 405

    resource_uri = reverse("api:message-draft-detail", kwargs={"pk": message_id})
    response = client.delete(resource_uri)
    assert response.status_code == 404

    # user send a message to public body
    response = client.post(
        "/api/v1/message/draft/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "kind": "post",
            "recipient_public_body": reverse(
                "api:publicbody-detail", kwargs={"pk": public_body.pk}
            ),
            "sender_public_body": None,
            "is_response": False,
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    print(response.json())

    message_id = response.json()["id"]
    publish_uri = reverse("api:message-draft-publish", kwargs={"pk": message_id})

    response = client.post(publish_uri)
    assert response.status_code == 200

    # ensure event was created
    assert FoiEvent.objects.get(
        message=message_id, event_name="message_sent", user=user
    )


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
    assert response.status_code == 404

    client.login(email=user2.email, password="froide")
    response = client.get(resource_uri)
    assert response.status_code == 404
