from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from froide.document.factories import DocumentFactory
from froide.foirequest.models.event import FoiEvent
from froide.foirequest.models.message import MessageKind
from froide.foirequest.tests import factories
from froide.upload.factories import UploadFactory


@pytest.mark.django_db
def test_upload_attachment(client: Client, user):
    request = factories.FoiRequestFactory.create(user=user)
    message = factories.FoiMessageFactory.create(request=request, kind=MessageKind.POST)
    draft_message = factories.FoiMessageDraftFactory.create(
        request=request, kind=MessageKind.POST
    )
    other_user = factories.UserFactory.create()
    upload = UploadFactory.create(user=other_user)

    # needs to be logged in
    response = client.post(
        "/api/v1/attachment/",
        data={
            "message": reverse("api:message-detail", kwargs={"pk": message.pk}),
            "upload": reverse("api:upload-detail", kwargs={"guid": upload.guid}),
        },
        content_type="application/json",
    )
    assert response.status_code == 401

    assert client.login(email=user.email, password="froide")

    # wrong user
    response = client.post(
        "/api/v1/attachment/",
        data={
            "message": reverse("api:message-detail", kwargs={"pk": message.pk}),
            "upload": reverse("api:upload-detail", kwargs={"guid": upload.guid}),
        },
        content_type="application/json",
    )
    assert response.status_code == 400

    # everything correct
    upload = UploadFactory.create(user=user)
    response = client.post(
        "/api/v1/attachment/",
        data={
            "message": reverse("api:message-detail", kwargs={"pk": message.pk}),
            "upload": reverse("api:upload-detail", kwargs={"guid": upload.guid}),
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    # try with draft correct
    upload = UploadFactory.create(user=user)
    response = client.post(
        "/api/v1/attachment/",
        data={
            "message": reverse(
                "api:message-draft-detail", kwargs={"pk": draft_message.pk}
            ),
            "upload": reverse("api:upload-detail", kwargs={"guid": upload.guid}),
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    # TODO: test that file is properly saved and accessible via its url


@pytest.mark.django_db
def test_delete_attachment(client: Client, user):
    request = factories.FoiRequestFactory.create(user=user)
    message = factories.FoiMessageFactory.create(request=request, kind=MessageKind.POST)

    # needs to be logged in
    attachment = factories.FoiAttachmentFactory.create(belongs_to=message)
    response = client.delete(
        reverse("api:attachment-detail", kwargs={"pk": attachment.pk})
    )
    assert response.status_code == 401

    # wrong user
    other_user = factories.UserFactory.create()
    assert client.login(email=other_user.email, password="froide")
    response = client.delete(
        reverse("api:attachment-detail", kwargs={"pk": attachment.pk})
    )
    assert response.status_code == 403

    # everything good
    assert client.login(email=user.email, password="froide")
    response = client.delete(
        reverse("api:attachment-detail", kwargs={"pk": attachment.pk})
    )
    assert response.status_code == 204

    # too old
    attachment = factories.FoiAttachmentFactory.create(
        belongs_to=message, timestamp=timezone.now() - timedelta(days=2)
    )
    response = client.delete(
        reverse("api:attachment-detail", kwargs={"pk": attachment.pk})
    )
    assert response.status_code == 403

    # must be postal
    message = factories.FoiMessageFactory.create(request=request)
    attachment = factories.FoiAttachmentFactory.create(belongs_to=message)
    response = client.delete(
        reverse("api:attachment-detail", kwargs={"pk": attachment.pk})
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_convert_attachment(client: Client, user):
    request = factories.FoiRequestFactory.create(user=user)
    message = factories.FoiMessageFactory.create(request=request, kind=MessageKind.POST)

    image1 = factories.FoiAttachmentFactory.create(
        belongs_to=message, filetype="image/png"
    )
    image2 = factories.FoiAttachmentFactory.create(
        belongs_to=message, filetype="image/png"
    )

    data = {
        "title": "test",
        "message": reverse("api:message-detail", kwargs={"pk": message.pk}),
        "images": [
            {
                "attachment": reverse(
                    "api:attachment-detail", kwargs={"pk": image1.pk}
                ),
                "rotate": 0,
            },
            {
                "attachment": reverse(
                    "api:attachment-detail", kwargs={"pk": image2.pk}
                ),
                "rotate": 90,
            },
        ],
    }

    # needs to be logged in
    response = client.post(
        reverse("api:attachment-convert-to-pdf"),
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 401

    # wrong user
    other_user = factories.UserFactory.create()
    assert client.login(email=other_user.email, password="froide")
    response = client.post(
        reverse("api:attachment-convert-to-pdf"),
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 400

    # everything good
    assert client.login(email=user.email, password="froide")
    response = client.post(
        reverse("api:attachment-convert-to-pdf"),
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.json()

    assert data["name"] == "test.pdf"
    assert data["filetype"] == "application/pdf"
    assert data["is_converted"] is True

    image1.refresh_from_db()
    image2.refresh_from_db()
    assert image1.converted_id == data["id"]
    assert image2.converted_id == data["id"]

    # can only convert images from that message
    not_an_image = factories.FoiAttachmentFactory.create(belongs_to=message)
    data = {
        "title": "test",
        "message": reverse("api:message-detail", kwargs={"pk": message.pk}),
        "images": [
            {
                "attachment": reverse(
                    "api:attachment-detail", kwargs={"pk": not_an_image.pk}
                ),
                "rotate": 0,
            }
        ],
    }

    response = client.post(
        reverse("api:attachment-convert-to-pdf"),
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 400

    # can only convert images from that message
    not_that_message = factories.FoiAttachmentFactory.create(filetype="image/png")
    data = {
        "title": "test",
        "message": reverse("api:message-detail", kwargs={"pk": message.pk}),
        "images": [
            {
                "attachment": reverse(
                    "api:attachment-detail", kwargs={"pk": not_that_message.pk}
                ),
                "rotate": 0,
            }
        ],
    }

    response = client.post(
        reverse("api:attachment-convert-to-pdf"),
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_change_approval(client: Client, user):
    assert client.login(email=user.email, password="froide")

    request = factories.FoiRequestFactory.create(user=user)
    message = factories.FoiMessageFactory.create(request=request)

    # can unapprove recently approved attachments

    attachment = factories.FoiAttachmentFactory.create(
        belongs_to=message, approved=True, approved_timestamp=timezone.now()
    )

    response = client.post(
        reverse("api:attachment-unapprove", kwargs={"pk": attachment.pk})
    )
    data = response.json()
    assert response.status_code == 200
    assert data["approved"] is False

    event = FoiEvent.objects.get(
        event_name=FoiEvent.EVENTS.ATTACHMENT_DEPUBLISHED, message=message
    )
    assert event.context["attachment_id"] == str(attachment.pk)

    # can't unapprove old attachments

    attachment = factories.FoiAttachmentFactory.create(
        belongs_to=message,
        approved=True,
        approved_timestamp=timezone.now() - timedelta(days=3),
    )

    response = client.post(
        reverse("api:attachment-unapprove", kwargs={"pk": attachment.pk})
    )
    assert response.status_code == 403
    attachment.refresh_from_db()
    assert attachment.approved

    # can approve unapproved attachments

    attachment = factories.FoiAttachmentFactory.create(
        belongs_to=message, approved=False
    )

    response = client.post(
        reverse("api:attachment-approve", kwargs={"pk": attachment.pk})
    )
    data = response.json()
    assert response.status_code == 200
    assert data["approved"] is True

    event = FoiEvent.objects.get(
        event_name=FoiEvent.EVENTS.ATTACHMENT_APPROVED, message=message
    )
    assert event.context["attachment_id"] == str(attachment.pk)

    # can't approve, when can_unapprove is False

    attachment = factories.FoiAttachmentFactory.create(
        belongs_to=message, approved=False, can_approve=False
    )

    response = client.post(
        reverse("api:attachment-approve", kwargs={"pk": attachment.pk})
    )
    assert response.status_code == 403
    attachment.refresh_from_db()
    assert not attachment.approved


@pytest.mark.django_db
def test_to_document(client: Client, user):
    assert client.login(email=user.email, password="froide")

    request = factories.FoiRequestFactory.create(user=user)
    message = factories.FoiMessageFactory.create(request=request)

    # can't convert unapprovable attachments
    attachment = factories.FoiAttachmentFactory.create(
        belongs_to=message, can_approve=False
    )

    response = client.post(
        reverse("api:attachment-to-document", kwargs={"pk": attachment.pk})
    )
    assert response.status_code == 403

    # must be a pdf
    attachment = factories.FoiAttachmentFactory.create(
        belongs_to=message, filetype="image/png"
    )
    response = client.post(
        reverse("api:attachment-to-document", kwargs={"pk": attachment.pk})
    )
    assert response.status_code == 400

    # has no document
    document = DocumentFactory.create()
    attachment = factories.FoiAttachmentFactory.create(
        belongs_to=message, document=document
    )

    response = client.post(
        reverse("api:attachment-to-document", kwargs={"pk": attachment.pk})
    )
    assert response.status_code == 400

    # everything good
    attachment = factories.FoiAttachmentFactory.create(belongs_to=message)

    response = client.post(
        reverse("api:attachment-to-document", kwargs={"pk": attachment.pk})
    )
    data = response.json()
    assert response.status_code == 201
    assert data["title"] == attachment.name
    assert str(request.pk) in data["foirequest"]
    assert str(message.sender_public_body.pk) in data["publicbody"]
