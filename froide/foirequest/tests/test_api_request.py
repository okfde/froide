import json
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

import pytest
from oauth2_provider.models import get_access_token_model, get_application_model

from froide.foirequest.models import FoiAttachment, FoiRequest
from froide.foirequest.models.event import FoiEvent
from froide.foirequest.models.request import Resolution, Status
from froide.foirequest.serializers import FoiMessageSerializer
from froide.foirequest.tests import factories
from froide.publicbody.models import PublicBody
from froide.upload.models import Upload

User = get_user_model()
Application = get_application_model()
AccessToken = get_access_token_model()


class ApiTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()
        self.test_user = User.objects.get(username="dummy")

    def test_list(self):
        response = self.client.get("/api/v1/request/")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/v1/message/")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/v1/attachment/")
        self.assertEqual(response.status_code, 200)

    def test_detail(self):
        req = FoiRequest.objects.all()[0]
        response = self.client.get("/api/v1/request/%d/" % req.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, req.title)
        self.assertNotContains(response, req.secret_address)
        req.user.private = True
        req.user.save()

        mes = factories.FoiMessageFactory.create(
            request=req,
            subject=req.user.get_full_name(),
            plaintext="Hallo %s,\n%s\n%s"
            % (req.user.get_full_name(), req.secret_address, req.user.address),
        )
        response = self.client.get("/api/v1/message/%d/" % mes.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, req.user.get_full_name())
        self.assertNotContains(response, req.secret_address)
        self.assertNotContains(response, req.user.address)

        att = FoiAttachment.objects.all()[0]
        att.approved = True
        att.save()
        response = self.client.get("/api/v1/attachment/%d/" % att.pk)
        self.assertEqual(response.status_code, 200)

    def test_permissions(self):
        req = factories.FoiRequestFactory.create(
            visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER, site=self.site
        )

        response = self.client.get("/api/v1/request/%d/" % req.pk)
        self.assertEqual(response.status_code, 404)

        mes = factories.FoiMessageFactory.create(request=req)
        response = self.client.get("/api/v1/message/%d/" % mes.pk)
        self.assertEqual(response.status_code, 404)

        att = factories.FoiAttachmentFactory.create(belongs_to=mes)
        att.approved = True
        att.save()
        response = self.client.get("/api/v1/attachment/%d/" % att.pk)
        self.assertEqual(response.status_code, 404)

    def test_content_hidden(self):
        marker = "TESTMARKER"
        mes = factories.FoiMessageFactory.create(
            content_hidden=True,
            plaintext=marker,
            plaintext_redacted=marker,
            subject=marker,
            subject_redacted=marker,
        )
        response = self.client.get("/api/v1/message/%d/" % mes.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, marker)

    def test_username_hidden(self):
        user = factories.UserFactory.create(first_name="Reinhardt")
        user.private = True
        user.save()
        mes = factories.FoiMessageFactory.create(sender_user=user)
        response = self.client.get("/api/v1/message/%d/" % mes.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, user.username)
        self.assertNotContains(response, user.first_name)

    def test_search(self):
        response = self.client.get("/api/v1/request/search/?q=Number")
        self.assertEqual(response.status_code, 200)

    def test_search_similar(self):
        factories.delete_index()
        search_url = "/api/v1/request/search/"
        response = self.client.get(search_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"objects":[]')
        self.assertEqual(response["Content-Type"], "application/json")
        req = FoiRequest.objects.all()[0]
        factories.rebuild_index()
        response = self.client.get("%s?%s" % (search_url, urlencode({"q": req.title})))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "title")
        self.assertContains(response, "description")


class OAuthAPIMixin:
    def setUp(self):
        factories.make_world()
        self.test_user = User.objects.get(username="dummy")
        self.dev_user = User.objects.create_user(
            "dev@example.com", "dev_user", "123456"
        )

        self.application = Application.objects.create(
            name="Test Application",
            redirect_uris="http://localhost http://example.com http://example.org",
            user=self.dev_user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )

        self.access_token = AccessToken.objects.create(
            user=self.test_user,
            scope="read:user",
            expires=timezone.now() + timedelta(seconds=300),
            token="secret-access-token-key",
            application=self.application,
        )

        self.req = factories.FoiRequestFactory.create(
            visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER,
            user=self.test_user,
            title="permissions required",
        )
        self.mes = factories.FoiMessageFactory.create(request=self.req)
        self.att = factories.FoiAttachmentFactory.create(
            belongs_to=self.mes, approved=False
        )
        self.att2 = factories.FoiAttachmentFactory.create(
            belongs_to=self.mes, approved=True
        )
        factories.FoiRequestFactory.create(
            visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER,
            user=self.dev_user,
            title="never shown",
        )
        self.pb = PublicBody.objects.all()[0]
        self.request_list_url = reverse("api:request-list")
        self.message_detail_url = reverse(
            "api:message-detail", kwargs={"pk": self.mes.pk}
        )

    def _create_authorization_header(self, token):
        return "Bearer {0}".format(token)

    def api_get(self, url):
        auth = self._create_authorization_header(self.access_token.token)
        response = self.client.get(url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)
        return response, json.loads(response.content.decode("utf-8"))

    def api_post(self, url, data=""):
        auth = self._create_authorization_header(self.access_token.token)
        response = self.client.post(
            url,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=auth,
        )
        return response, json.loads(response.content.decode("utf-8"))

    def api_delete(self, url, data=""):
        auth = self._create_authorization_header(self.access_token.token)
        response = self.client.delete(
            url,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=auth,
        )
        result = None
        if response.content:
            result = json.loads(response.content.decode("utf-8"))
        return response, result


class OAuthApiTest(OAuthAPIMixin, TestCase):
    def test_list_public_requests(self):
        self.assertEqual(FoiRequest.objects.all().count(), 3)
        response = self.client.get(self.request_list_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode("utf-8"))
        self.assertEqual(result["meta"]["total_count"], 1)

    def test_list_private_requests_when_logged_in(self):
        self.client.login(email=self.test_user.email, password="froide")
        response = self.client.get(self.request_list_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode("utf-8"))
        self.assertEqual(result["meta"]["total_count"], 2)
        self.client.logout()

    def test_list_private_requests_without_scope(self):
        response, result = self.api_get(self.request_list_url)
        self.assertEqual(result["meta"]["total_count"], 1)
        self.assertNotContains(response, "permissions required")
        self.assertNotContains(response, "never shown")

    def test_list_private_requests_with_scope(self):
        self.access_token.scope = "read:user read:request"
        self.access_token.save()

        response, result = self.api_get(self.request_list_url)
        self.assertEqual(result["meta"]["total_count"], 2)
        self.assertContains(response, "permissions required")
        self.assertNotContains(response, "never shown")

    def test_filter_other_private_requests(self):
        self.access_token.scope = "read:user read:request"
        self.access_token.save()

        response, result = self.api_get(
            self.request_list_url + "?user=%s" % self.dev_user.pk
        )
        self.assertEqual(result["meta"]["total_count"], 0)

    def test_filter_private_requests_without_scope(self):
        response, result = self.api_get(
            self.request_list_url + "?user=%s" % self.test_user.pk
        )
        self.assertEqual(result["meta"]["total_count"], 0)

    def test_filter_private_requests_with_scope(self):
        self.access_token.scope = "read:user read:request"
        self.access_token.save()

        response, result = self.api_get(
            self.request_list_url + "?user=%s" % self.test_user.pk
        )
        self.assertEqual(result["meta"]["total_count"], 1)

    def test_see_only_approved_attachments(self):
        self.req.visibility = FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC
        self.req.save()

        self.assertEqual(FoiAttachment.objects.all().count(), 4)
        response = self.client.get(self.message_detail_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(result["attachments"]), 1)

    def test_see_only_approved_attachments_loggedin(self):
        self.req.visibility = FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC
        self.req.save()

        self.client.login(email=self.test_user.email, password="froide")
        response = self.client.get(self.message_detail_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(result["attachments"]), 2)

    def test_see_only_approved_attachments_without_scope(self):
        self.req.visibility = FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC
        self.req.save()

        response, result = self.api_get(self.message_detail_url)
        self.assertEqual(len(result["attachments"]), 1)

    def test_see_only_approved_attachments_with_scope(self):
        self.req.visibility = FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC
        self.req.save()

        self.access_token.scope = "read:user read:request"
        self.access_token.save()

        response, result = self.api_get(self.message_detail_url)
        self.assertEqual(len(result["attachments"]), 2)

    def test_request_creation_not_loggedin(self):
        old_count = FoiRequest.objects.all().count()
        response = self.client.post(
            self.request_list_url,
            json.dumps(
                {"subject": "Test", "body": "Testing", "publicbodies": [self.pb.pk]}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        new_count = FoiRequest.objects.all().count()
        self.assertEqual(old_count, new_count)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_creation_without_scope(self):
        old_count = FoiRequest.objects.all().count()
        response, result = self.api_post(
            self.request_list_url,
            {"subject": "Test", "body": "Testing", "publicbodies": [self.pb.pk]},
        )
        self.assertEqual(response.status_code, 403)
        new_count = FoiRequest.objects.all().count()
        self.assertEqual(old_count, new_count)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_creation_with_scope(self):
        self.access_token.scope = "read:user make:request"
        self.access_token.save()

        old_count = FoiRequest.objects.all().count()
        mail.outbox = []
        data = {
            "subject": "OAUth-Test",
            "body": "Testing",
            "publicbodies": [self.pb.pk],
            "tags": ["test1", "test2"],
        }
        response, result = self.api_post(self.request_list_url, data)
        self.assertEqual(response.status_code, 201)
        new_count = FoiRequest.objects.all().count()
        self.assertEqual(old_count, new_count - 1)
        self.assertEqual(len(mail.outbox), 2)
        new_req = FoiRequest.objects.get(title="OAUth-Test")
        self.assertEqual({t.name for t in new_req.tags.all()}, set(data["tags"]))

        # Check throttling
        froide_config = dict(settings.FROIDE_CONFIG)
        froide_config["request_throttle"] = [(1, 60), (5, 60 * 60)]
        with self.settings(FROIDE_CONFIG=froide_config):
            response, result = self.api_post(
                self.request_list_url,
                {"subject": "Test", "body": "Testing", "publicbodies": [self.pb.pk]},
            )
        self.assertEqual(response.status_code, 429)

    def test_foiattachment_upload(self):
        mes = factories.FoiMessageFactory.create(request=self.req, kind="post")
        mes_url = reverse("api:message-detail", kwargs={"pk": mes.pk})
        att_url = reverse("api:attachment-list")

        upload = Upload.objects.create(
            state="done",
            filename="test.pdf",
            user=self.test_user,
            upload_metadata='{"filetype": "application/pdf"}',
        )
        upload_url = reverse("api:upload-detail", kwargs={"guid": str(upload.guid)})

        response, result = self.api_post(
            att_url, {"message": mes_url, "upload": upload_url}
        )
        assert response.status_code == 403

        # Set correct scope
        self.access_token.scope = "read:request write:message write:attachment"
        self.access_token.save()

        fake_upload_url = "y" + upload_url[1:]
        response, result = self.api_post(
            att_url, {"message": mes_url, "upload": fake_upload_url}
        )
        assert response.status_code == 400

        response, result = self.api_post(
            att_url, {"message": mes_url, "upload": upload_url}
        )
        assert response.status_code == 201


@pytest.mark.django_db
def test_redacted_description(world, client):
    fr = FoiRequest.objects.all()[0]
    fr.description = "This is a test description"
    fr.description_redacted = "This is a [redacted] description"
    fr.save()
    response = client.get("/api/v1/request/%d/" % fr.pk)
    assert response.status_code == 200
    assert fr.description not in str(response.json())
    assert fr.description_redacted in str(response.json())
    assert fr.description_redacted in str(response.json())


@pytest.fixture
def many_attachment_foimessage(foi_message):
    for i in range(100):
        red_att = FoiAttachment(
            belongs_to=foi_message,
            name=f"{i}_redacted.pdf",
            is_redacted=True,
            filetype="application/pdf",
            approved=True,
            can_approve=True,
        )
        red_att.approve_and_save()
        orig_att = FoiAttachment(
            belongs_to=foi_message,
            name=f"{i}.pdf",
            is_redacted=False,
            filetype="application/pdf",
            approved=False,
            can_approve=False,
            redacted=red_att,
        )
        orig_att.approve_and_save()
    return foi_message


def selective_equal_dicts(a, b, ignore_keys):
    ka = set(a).difference(ignore_keys)
    kb = set(b).difference(ignore_keys)
    return ka == kb and all(a[k] == b[k] for k in ka)


@pytest.mark.django_db
def test_foi_message_serializer_performance(world, client, many_attachment_foimessage):
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    with CaptureQueriesContext(connection) as ctx:
        serializer = FoiMessageSerializer(
            many_attachment_foimessage, context={"request": request}
        )
        data = serializer.data
        assert len(ctx.captured_queries) < 10

    with CaptureQueriesContext(connection) as ctx:
        api_data = client.get(
            reverse("api:message-detail", kwargs={"pk": many_attachment_foimessage.pk})
        )
        assert len(ctx.captured_queries) < 10
        assert api_data.json().keys() == data.keys()
        assert len(api_data.json()["attachments"]) == len(data["attachments"])
        for (
            a,
            b,
        ) in zip(api_data.json()["attachments"], data["attachments"], strict=True):
            assert selective_equal_dicts(a, b, {"file_url"})


@pytest.mark.django_db
def test_foirequest_update(client, user):
    request = factories.FoiRequestFactory.create(user=user)
    law = factories.FoiLawFactory()

    # must be logged in
    response = client.patch(
        reverse("api:request-detail", kwargs={"pk": request.pk}),
        data={"law": reverse("api:law-detail", kwargs={"pk": law.pk})},
        content_type="application/json",
    )
    assert response.status_code == 401

    # must be the owner
    other_user = factories.UserFactory.create()
    assert client.login(email=other_user.email, password="froide")

    response = client.patch(
        reverse("api:request-detail", kwargs={"pk": request.pk}),
        data={"law": reverse("api:law-detail", kwargs={"pk": law.pk})},
        content_type="application/json",
    )
    assert response.status_code == 404

    # can update some fields
    assert client.login(email=user.email, password="froide")

    response = client.patch(
        reverse("api:request-detail", kwargs={"pk": request.pk}),
        data={"law": reverse("api:law-detail", kwargs={"pk": law.pk})},
        content_type="application/json",
    )
    assert str(law.pk) in response.json()["law"]
    assert response.status_code == 200

    refusal_reason = law.get_refusal_reason_choices()

    response = client.patch(
        reverse("api:request-detail", kwargs={"pk": request.pk}),
        data={
            "costs": 2.34,
            "status": Status.RESOLVED,
            "resolution": Resolution.REFUSED,
            "refusal_reason": refusal_reason[0][0],
            "summary": "Lorem ipsum",
            "tags": ["foo", "bar"],
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["costs"] == 2.34
    assert data["resolution"] == Resolution.REFUSED
    assert data["refusal_reason"] == refusal_reason[0][0]
    assert data["summary"] == "Lorem ipsum"
    assert data["tags"] == ["foo", "bar"]

    assert FoiEvent.objects.get(
        request=request,
        event_name=FoiEvent.EVENTS.REPORTED_COSTS,
        context__costs="2.34",
    )
    assert FoiEvent.objects.get(
        request=request,
        event_name=FoiEvent.EVENTS.STATUS_CHANGED,
        context__status=Status.RESOLVED,
        context__resolution=Resolution.REFUSED,
        context__costs="2.34",
        context__refusal_reason=refusal_reason[0][0],
        context__previous_status="",
        context__previous_resolution="",
    )

    # can't update read-only fields
    pb = factories.PublicBodyFactory()
    response = client.patch(
        reverse("api:request-detail", kwargs={"pk": request.pk}),
        data={
            "is_foi": False,
            "public_body": reverse("api:publicbody-detail", kwargs={"pk": pb.pk}),
            "slug": "foo",
            "reference": "bar",
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_foi"] is True
    assert str(pb.pk) not in data["public_body"]
    assert data["slug"] == request.slug
    assert data["reference"] == request.reference

    # can't set the status to system-only values
    response = client.patch(
        reverse("api:request-detail", kwargs={"pk": request.pk}),
        data={"status": Status.PUBLICBODY_NEEDED},
        content_type="application/json",
    )
    assert response.status_code == 400
