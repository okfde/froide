from datetime import datetime, timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest
from oauth2_provider.models import get_access_token_model, get_application_model

from ..models import FoiEvent, FoiRequest
from ..models.message import MessageKind
from ..tests import factories

Application = get_application_model()
AccessToken = get_access_token_model()


@pytest.mark.django_db
def test_message(client: Client, user):
    assert client.login(email=user.email, password="froide")

    request = factories.FoiRequestFactory.create(
        user=user, created_at=timezone.make_aware(datetime(2000, 1, 1))
    )
    other_request = factories.FoiRequestFactory.create()
    message = factories.FoiMessageFactory.create(request=request)

    # can't create an email message
    response = client.post(
        reverse("api:message-list"),
        data={
            "request": reverse("api:request-detail", kwargs={"pk": 1}),
            "kind": "email",
        },
        content_type="application/json",
    )
    assert response.status_code == 400

    timestamp = "2000-01-01T00:00:00+00:00"

    # must be a postal message
    response = client.patch(
        reverse("api:message-detail", kwargs={"pk": message.pk}),
        data={
            "registered_mail_date": timestamp,
        },
        content_type="application/json",
    )
    assert response.status_code == 403

    # can only update some fields
    message = factories.FoiMessageFactory.create(
        request=request, kind=MessageKind.POST, timestamp=timezone.now()
    )
    response = client.patch(
        reverse("api:message-detail", kwargs={"pk": message.pk}),
        data={
            "sent": False,
            "kind": MessageKind.EMAIL,
            "request": reverse("api:request-detail", kwargs={"pk": other_request.pk}),
            "is_draft": True,
            "not_publishable": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 400

    # nothing changed, so no event
    with pytest.raises(FoiEvent.DoesNotExist):
        FoiEvent.objects.get(
            event_name=FoiEvent.EVENTS.MESSAGE_EDITED, message=message, user=user
        )

    # can update some fields
    response = client.patch(
        reverse("api:message-detail", kwargs={"pk": message.pk}),
        data={
            "registered_mail_date": timestamp,
            "timestamp": timestamp,
        },
        content_type="application/json",
    )
    data = response.json()
    assert response.status_code == 200
    assert "2000-01-01" in data["registered_mail_date"]
    assert "2000-01-01" in data["timestamp"]
    assert "12:00:00" in data["timestamp"]  # converted to postal time

    event = FoiEvent.objects.get(
        event_name=FoiEvent.EVENTS.MESSAGE_EDITED, message=message, user=user
    )
    assert "2000-01-01" in event.context["registered_mail_date"]
    assert "2000-01-01" in event.context["timestamp"]
    assert "12:00:00" in event.context["timestamp"]  # converted to postal time

    # can't delete
    response = client.delete(reverse("api:message-detail", kwargs={"pk": message.pk}))
    assert response.status_code == 405


@pytest.mark.django_db
def test_message_draft(client: Client, user):
    other_user = factories.UserFactory.create()
    request = factories.FoiRequestFactory.create(user=user)
    assert client.login(email=user.email, password="froide")

    # can't create an email
    response = client.post(
        "/api/v1/message/",
        data={
            "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
            "kind": "email",
        },
        content_type="application/json",
    )
    assert response.status_code == 400, response.json()

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
        "/api/v1/message/",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 201, response.json()
    message_response = response.json()
    assert message_response["is_draft"]

    message_id = message_response["id"]
    resource_uri = reverse("api:message-detail", kwargs={"pk": message_id})

    # Can't delete drafts
    response = client.delete(resource_uri)
    assert response.status_code == 405, response.json()

    # creating it again, returns same draft
    response = client.post(
        "/api/v1/message/",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()

    new_message_id = response.json()["id"]
    assert message_id == new_message_id
    resource_uri = reverse("api:message-detail", kwargs={"pk": message_id})

    # can't set sent stauts
    assert response.json()["sent"] is True
    response = client.patch(
        resource_uri, data={"sent": False}, content_type="application/json"
    )
    assert response.json()["sent"] is True

    # appears in regular messages
    response = client.get(reverse("api:message-detail", kwargs={"pk": message_id}))
    assert response.status_code == 200

    # and appears in drafts list
    response = client.get(reverse("api:message-list") + "?is_draft=1")
    assert response.status_code == 200
    assert resource_uri in str(response.content)

    # and appears in filtered drafts list
    response = client.get(
        reverse("api:message-list") + f"?is_draft=1&request={request.pk}"
    )
    assert response.status_code == 200
    assert resource_uri in str(response.content)

    # but not for logged out users
    client.logout()
    response = client.get(reverse("api:message-detail", kwargs={"pk": message_id}))
    assert response.status_code == 404

    response = client.get(reverse("api:message-list") + "?is_draft=1")
    assert response.status_code == 200
    assert resource_uri not in str(response.content)

    response = client.get(
        reverse("api:message-list") + f"?is_draft=1&request={request.pk}"
    )
    assert response.status_code == 200
    assert resource_uri not in str(response.content)

    # and not for other users
    client.force_login(other_user)
    response = client.get(reverse("api:message-detail", kwargs={"pk": message_id}))
    assert response.status_code == 404

    response = client.get(reverse("api:message-list") + "?is_draft=1")
    assert response.status_code == 200
    assert resource_uri not in str(response.content)

    response = client.get(
        reverse("api:message-list") + f"?is_draft=1&request={request.pk}"
    )
    assert response.status_code == 200
    assert resource_uri not in str(response.content)

    client.logout()
    assert client.login(email=user.email, password="froide")

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
        "/api/v1/message/",
        data=request_data,
        content_type="application/json",
    )
    data = response.json()
    assert response.status_code == 200
    assert reverse("api:request-detail", kwargs={"pk": request.pk}) in data["request"]

    message_id = response.json()["id"]
    publish_uri = reverse("api:message-publish", kwargs={"pk": message_id})

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

    # create + publish another message draft
    response = client.post(
        "/api/v1/message/",
        data=request_data,
        content_type="application/json",
    )
    assert response.status_code == 201

    message_id = response.json()["id"]
    publish_uri = reverse("api:message-publish", kwargs={"pk": message_id})

    response = client.post(publish_uri)
    assert response.status_code == 200
    data = response.json()

    # check date is correct - one second after the other one!
    assert "12:00:01" in data["timestamp"]


@pytest.mark.django_db
def test_draft_auth(client, user):
    other_user = factories.UserFactory.create()
    other_request = factories.FoiRequestFactory.create(user=other_user)

    data = {
        "request": reverse("api:request-detail", kwargs={"pk": other_request.pk}),
        "kind": "post",
        "is_response": True,
        "sender_public_body": reverse(
            "api:publicbody-detail", kwargs={"pk": other_request.public_body.pk}
        ),
    }

    # need to be logged in
    client.logout()
    response = client.post(
        "/api/v1/message/",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 401

    # can't publish drafts
    draft = factories.FoiMessageFactory.create(request=other_request, is_draft=True)
    response = client.post(reverse("api:message-publish", kwargs={"pk": draft.pk}))
    assert response.status_code == 401

    # needs to be own request
    client.login(email=user.email, password="froide")
    response = client.post(
        "/api/v1/message/",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 400

    # create message draft
    request = factories.FoiRequestFactory.create(user=user)
    data = {
        "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
        "kind": "post",
        "is_response": True,
        "sender_public_body": reverse(
            "api:publicbody-detail", kwargs={"pk": request.public_body.pk}
        ),
    }

    response = client.post(
        "/api/v1/message/",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 201, response.json()
    resource_uri = response.json()["resource_uri"]

    # can't change it to other's people request
    response = client.patch(
        resource_uri,
        data={
            "request": reverse("api:request-detail", kwargs={"pk": other_request.pk}),
        },
        content_type="application/json",
    )
    assert response.status_code == 400

    # drafts can't be seen by others
    client.logout()
    response = client.get(resource_uri)
    assert response.status_code == 404

    client.login(email=other_user.email, password="froide")
    response = client.get(resource_uri)
    assert response.status_code == 404


@pytest.fixture
def get_oauth_header(dummy_user):
    application = Application.objects.create(
        name="Test Application",
        redirect_uris="http://localhost http://example.com http://example.org",
        user=dummy_user,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
    )

    def make_token(scope):
        access_token = AccessToken.objects.create(
            user=dummy_user,
            scope=scope,
            expires=timezone.now() + timedelta(seconds=300),
            token="secret-access-token-key",
            application=application,
        )
        return "Bearer {0}".format(access_token.token)

    return make_token


@pytest.mark.django_db
def test_private_message_api(client, dummy_user, get_oauth_header):
    foirequest = factories.FoiRequestFactory.create(
        user=dummy_user, visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER
    )
    foimessage = factories.FoiMessageFactory.create(
        request=foirequest,
        kind=MessageKind.POST,
        is_draft=True,
    )

    working_scopes = " ".join(
        [
            "read:request",
        ]
    )

    auth_header = get_oauth_header(working_scopes)
    foirequest_url = reverse("api:request-detail", kwargs={"pk": foirequest.pk})
    response = client.get(foirequest_url, HTTP_AUTHORIZATION=auth_header)
    assert response.status_code == 200

    foimessage_list_url = reverse("api:message-list") + "?request={}".format(
        foirequest.pk
    )
    response = client.get(foimessage_list_url, HTTP_AUTHORIZATION=auth_header)
    assert response.status_code == 200
    assert len(response.json()["objects"]) == 1

    foimessage_url = reverse("api:message-detail", kwargs={"pk": foimessage.pk})
    response = client.get(foimessage_url, HTTP_AUTHORIZATION=auth_header)
    assert response.status_code == 200


@pytest.mark.django_db
def test_private_message_api_insufficient(client, dummy_user, get_oauth_header):
    foirequest = factories.FoiRequestFactory.create(
        user=dummy_user, visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER
    )
    foimessage = factories.FoiMessageFactory.create(
        request=foirequest,
        kind=MessageKind.POST,
        is_draft=True,
    )

    bad_scopes = " ".join(
        [
            "write:request",
        ]
    )

    auth_header = get_oauth_header(bad_scopes)
    foirequest_url = reverse("api:request-detail", kwargs={"pk": foirequest.pk})
    response = client.get(foirequest_url, HTTP_AUTHORIZATION=auth_header)
    assert response.status_code == 404

    foimessage_list_url = reverse("api:message-list") + "?request={}".format(
        foirequest.pk
    )
    response = client.get(foimessage_list_url, HTTP_AUTHORIZATION=auth_header)
    assert response.status_code == 200
    assert len(response.json()["objects"]) == 0

    # make it public, but message is draft!
    foirequest.visibility = FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC
    foirequest.save()

    foimessage_url = reverse("api:message-detail", kwargs={"pk": foimessage.pk})
    response = client.get(foimessage_url, HTTP_AUTHORIZATION=auth_header)
    assert response.status_code == 404


@pytest.mark.django_db
def test_create_draft_message_with_oauth(client, dummy_user, get_oauth_header):
    request = factories.FoiRequestFactory.create(user=dummy_user)
    working_scopes = " ".join(
        [
            "write:request",
            "write:message",
        ]
    )

    data = {
        "request": reverse("api:request-detail", kwargs={"pk": request.pk}),
        "kind": "post",
        "is_response": True,
        "sender_public_body": reverse(
            "api:publicbody-detail", kwargs={"pk": request.public_body.pk}
        ),
    }
    auth_header = get_oauth_header(working_scopes)
    response = client.post(
        "/api/v1/message/",
        data=data,
        HTTP_AUTHORIZATION=auth_header,
        content_type="application/json",
    )
    assert response.status_code == 201, response.json()
    message_response = response.json()
    assert message_response["is_draft"]
