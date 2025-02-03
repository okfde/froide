from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from froide.foirequest.models.message import MessageKind
from froide.foirequest.tests import factories
from froide.upload.factories import UploadFactory


@pytest.mark.django_db
def test_upload_attachment(client: Client, user):
    request = factories.FoiRequestFactory.create(user=user)
    message = factories.FoiMessageFactory.create(request=request, kind=MessageKind.POST)
    upload = UploadFactory.create(user=user)

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

    # add attachment to message
    response = client.post(
        "/api/v1/attachment/",
        data={
            "message": reverse("api:message-detail", kwargs={"pk": message.pk}),
            "upload": reverse("api:upload-detail", kwargs={"guid": upload.guid}),
        },
        content_type="application/json",
    )
    assert response.status_code == 201


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
