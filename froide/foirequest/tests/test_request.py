import copy
import os
import re
import zipfile
from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
from email.parser import BytesParser as Parser
from io import BytesIO
from unittest import mock
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.http import QueryDict
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

import pytest
import time_machine
from pytest_django.asserts import assertContains, assertFormError, assertNotContains

from froide.foirequest.foi_mail import (
    add_message_from_email,
    generate_foirequest_files,
    package_foirequest,
)
from froide.foirequest.forms import get_escalation_message_form, get_send_message_form
from froide.foirequest.models import (
    DeliveryStatus,
    FoiAttachment,
    FoiMessage,
    FoiRequest,
)
from froide.foirequest.models.message import MessageKind
from froide.foirequest.signals import email_left_queue
from froide.foirequest.tests import factories
from froide.foirequest.utils import possible_reply_addresses
from froide.helper.content_urls import get_content_url
from froide.helper.email_parsing import EmailAddress, ParsedEmail
from froide.publicbody.models import FoiLaw, PublicBody

User = get_user_model()


@pytest.fixture
def msgobj():
    return Parser().parse(BytesIO())


def assert_forbidden(response):
    assert response.status_code == 302
    assert reverse("account-login") in response["Location"]
    assert "?next=" in response["Location"]


@pytest.mark.django_db
def test_public_body_logged_in_request(world, client, pb):
    ok = client.login(email="info@fragdenstaat.de", password="froide")
    assert ok

    user = User.objects.get(username="sw")
    user.organization_name = "ACME Org"
    user.save()

    pb = PublicBody.objects.all()[0]
    old_number = pb.number_of_requests
    post = {
        "subject": "Test-Subject",
        "body": "This is another test body with Ümläut€n",
        "publicbody": pb.pk,
        "public": False,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302
    req = FoiRequest.objects.filter(user=user, public_body=pb).order_by("-id")[0]
    assert req is not None
    assert not req.public
    assert req.status == "awaiting_response"
    assert req.visibility == 1
    assert old_number + 1 == req.public_body.number_of_requests
    assert req.title == post["subject"]
    message = req.foimessage_set.all()[0]
    assert post["body"] in message.plaintext
    assert "\n%s\n" % user.get_full_name() in message.plaintext
    client.logout()
    response = client.post(
        reverse("foirequest-make_public", kwargs={"slug": req.slug}), {}
    )
    assert_forbidden(response)
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(
        reverse("foirequest-make_public", kwargs={"slug": req.slug}), {}
    )
    assert response.status_code == 302
    req = FoiRequest.published.get(id=req.id)
    assert req.public
    assert req.messages[-1].subject.count("[#%s]" % req.pk) == 1
    assert req.messages[-1].subject.endswith("[#%s]" % req.pk)


@pytest.mark.django_db
def test_public_body_new_user_request(world, client, pb):
    client.logout()
    factories.UserFactory.create(email="dummy@example.com")
    pb = PublicBody.objects.all()[0]
    post = {
        "subject": "Test-Subject With New User",
        "body": "This is a test body with new user",
        "first_name": "Stefan",
        "last_name": "Wehrmeyer",
        "address": "TestStreet 3\n55555 Town",
        "user_email": "sw@example.com",
        "terms": "on",
        "public": False,
        "private": True,
        "publicbody": pb.pk,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302
    user = User.objects.filter(email=post["user_email"]).get()
    assert not user.is_active
    req = FoiRequest.objects.filter(user=user, public_body=pb).get()
    assert req.title == post["subject"]
    assert req.description == post["body"]
    assert req.status == "awaiting_user_confirmation"
    assert req.visibility == 0
    message = req.foimessage_set.all()[0]
    assert post["body"] in message.plaintext
    assert post["body"] in message.content
    assert post["body"] in message.get_real_content()
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert mail.outbox[0].to[0] == post["user_email"]
    match = re.search(r"/%d/(\w+)/" % user.pk, message.body)
    match_full = re.search(r"http://[^/]+(/.+)", message.body)
    assert match is not None
    assert match_full is not None
    assert match is not None
    assert match_full is not None
    url = match_full.group(1)
    secret = match.group(1)
    generated_url = reverse(
        "account-confirm",
        kwargs={"user_id": user.pk, "secret": secret},
    )
    assert generated_url in url
    assert not user.is_active
    response = client.get(url, follow=True)
    assert response.status_code == 200

    req = FoiRequest.objects.get(pk=req.pk)
    mes = req.messages[0]
    mes.timestamp = mes.timestamp - timedelta(days=2)
    mes.save()
    assert req.status == "awaiting_response"
    assert req.visibility == 1
    assert len(mail.outbox) == 3
    message = mail.outbox[1]
    assert (
        "Legal Note: This mail was sent through a Freedom Of Information Portal."
        in message.body
    )
    assert req.secret_address in message.extra_headers.get("Reply-To", "")
    assert message.to[0] == req.public_body.email
    assert message.subject == "%s [#%s]" % (req.title, req.pk)


@pytest.mark.django_db
def test_new_email_received_set_status(world, client, pb, msgobj):
    req = FoiRequest.objects.all()[0]
    pb = req.public_body

    new_foi_email = "foi@" + pb.email.split("@")[1]
    add_message_from_email(
        req,
        ParsedEmail(
            msgobj,
            **{
                "date": timezone.now() - timedelta(days=1),
                "subject": "Re: %s" % req.title,
                "body": """Message""",
                "html": None,
                "from_": EmailAddress("FoI Officer", new_foi_email),
                "to": [EmailAddress(req.user.get_full_name(), req.secret_address)],
                "cc": [],
                "resent_to": [],
                "resent_cc": [],
                "attachments": [],
            },
        ),
    )
    req = FoiRequest.objects.get(pk=req.pk)

    assert req.awaits_classification()
    assert len(req.messages) == 3
    assert req.messages[-1].sender_email == new_foi_email
    assert req.messages[-1].sender_public_body == req.public_body

    client.force_login(req.user)
    response = client.get(reverse("foirequest-show", kwargs={"slug": req.slug}))
    assert response.status_code == 200
    assert req.status_settable
    response = client.post(
        reverse("foirequest-set_status", kwargs={"slug": req.slug}),
        {"status": "invalid_status_settings_now"},
    )
    assert response.status_code == 400
    costs = "123.45"
    status = "awaiting_response"
    response = client.post(
        reverse("foirequest-set_status", kwargs={"slug": req.slug}),
        {"status": status, "costs": costs},
    )
    req = FoiRequest.objects.get(pk=req.pk)
    assert req.costs == Decimal(costs)
    assert req.status == status


@pytest.mark.django_db
def test_send_message(world, client, pb):
    req = FoiRequest.objects.all()[0]
    pb = req.public_body
    new_foi_email = "foi@" + pb.email.split("@")[1]
    factories.FoiMessageFactory.create(
        request=req, sender_email=new_foi_email, sender_public_body=req.public_body
    )
    user = req.user
    # send reply
    old_len = len(mail.outbox)
    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), {}
    )
    assert_forbidden(response)

    client.force_login(user)
    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), {}
    )
    assert response.status_code == 400

    post = {
        "sendmessage-message": "My custom reply",
        "sendmessage-address": user.address,
        "sendmessage-send_address": "1",
    }
    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 400

    post["sendmessage-to"] = "abc"
    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 400

    post["sendmessage-to"] = "9" * 10
    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 400

    pb_email = req.public_body.email
    req.public_body.email = ""
    req.public_body.save()
    post["sendmessage-to"] = pb_email
    post["sendmessage-subject"] = "Re: Custom subject"
    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 400
    req.public_body.email = pb_email
    req.public_body.save()

    post["sendmessage-subject"] = "Re: Custom subject"
    assert new_foi_email in {x[0] for x in possible_reply_addresses(req)}
    post["sendmessage-to"] = new_foi_email
    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 302
    new_len = len(mail.outbox)
    assert old_len + 2 == new_len
    message = list(
        filter(lambda x: x.subject.startswith(post["sendmessage-subject"]), mail.outbox)
    )[-1]
    assert message.subject.endswith("[#%s]" % req.pk)
    assert message.body.startswith(post["sendmessage-message"])
    assert (
        "Legal Note: This mail was sent through a Freedom Of Information Portal."
        in message.body
    )
    assert user.address in message.body
    assert new_foi_email in message.to[0]
    req._messages = None
    foimessage = list(req.messages)[-1]
    req = FoiRequest.objects.get(pk=req.pk)
    assert req.last_message == foimessage.timestamp
    assert foimessage.recipient_public_body == req.public_body


@pytest.mark.django_db
def test_set_law(world, client):
    req = FoiRequest.objects.all()[0]
    client.force_login(req.user)
    other_laws = req.law.combined.all()
    assert req.law.meta
    response = client.post(
        reverse("foirequest-set_law", kwargs={"slug": req.slug}), {"law": "9" * 5}
    )
    assert response.status_code == 400

    post = {"law": str(other_laws[0].pk)}
    response = client.post(
        reverse("foirequest-set_law", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 302
    response = client.get(reverse("foirequest-show", kwargs={"slug": req.slug}))
    assert response.status_code == 200
    response = client.post(
        reverse("foirequest-set_law", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 302
    req = FoiRequest.objects.all()[0]
    assert not req.law.meta


@pytest.mark.django_db
def test_logged_out_actions_forbidden(world, client):
    req = FoiRequest.objects.all()[0]

    other_laws = req.law.combined.all()
    costs = "123.45"
    status = "awaiting_response"

    post = {"law": str(other_laws[0].pk)}
    client.logout()

    response = client.post(
        reverse("foirequest-set_law", kwargs={"slug": req.slug}), post
    )
    assert_forbidden(response)

    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
    )
    assert_forbidden(response)
    response = client.post(
        reverse("foirequest-set_status", kwargs={"slug": req.slug}),
        {"status": status, "costs": costs},
    )
    assert_forbidden(response)


@pytest.mark.django_db
def test_wrong_user_actions_forbidden(world, client):
    client.login(email="dummy@example.org", password="froide")

    req = FoiRequest.objects.all()[0]

    other_laws = req.law.combined.all()
    costs = "123.45"
    status = "awaiting_response"

    post = {"law": str(other_laws[0].pk)}

    response = client.post(
        reverse("foirequest-set_law", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 403
    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 403
    response = client.post(
        reverse("foirequest-set_status", kwargs={"slug": req.slug}),
        {"status": status, "costs": costs},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_public_body_not_logged_in_request(world, client, pb):
    client.logout()
    pb = PublicBody.objects.all()[0]
    response = client.post(
        reverse("foirequest-make_request"),
        {
            "subject": "Test-Subject",
            "body": "This is a test body",
            "user_email": "test@example.com",
            "publicbody": pb.pk,
        },
    )
    assert response.status_code == 400
    assertFormError(
        response.context["user_form"], "first_name", ["This field is required."]
    )
    assertFormError(
        response.context["user_form"], "last_name", ["This field is required."]
    )


@pytest.mark.django_db
def test_logged_in_request_with_public_body(world, client, pb):
    pb = PublicBody.objects.all()[0]
    client.login(email="dummy@example.org", password="froide")
    post = {
        "subject": "Another Third Test-Subject",
        "body": "This is another test body",
        "publicbody": "bs",
        "public": True,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 400
    post["law"] = str(pb.default_law.pk)
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 400
    post["publicbody"] = "9" * 10  # not that many in fixture
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 400
    post["publicbody"] = str(pb.pk)
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302
    req = FoiRequest.objects.get(title=post["subject"])
    assert req.public_body.pk == pb.pk
    assert req.messages[0].sent
    assert req.law == pb.default_law

    email_messages = list(
        filter(
            lambda x: req.secret_address in x.extra_headers.get("Reply-To", ""),
            mail.outbox,
        )
    )
    assert len(email_messages) == 1
    email_message = email_messages[0]
    assert email_message.to[0] == pb.email
    assert email_message.subject == "%s [#%s]" % (req.title, req.pk)
    assert (
        email_message.extra_headers.get("Message-Id")
        == req.messages[0].make_message_id()
    )


@pytest.mark.django_db
def test_redirect_after_request(world, client, pb):
    response = client.get(
        reverse("foirequest-make_request") + "?redirect=/speci4l-url/?blub=bla"
    )
    assertContains(response, 'value="/speci4l-url/?blub=bla"')

    pb = PublicBody.objects.all()[0]
    client.login(email="dummy@example.org", password="froide")

    post = {
        "subject": "Another Third Test-Subject",
        "body": "This is another test body",
        "redirect_url": "/foo/?blub=bla",
        "publicbody": str(pb.pk),
        "public": True,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302
    req = FoiRequest.objects.get(title=post["subject"])
    assert "/foo/?" in response["Location"]
    assert "blub=bla" in response["Location"]
    assert "request=%s" % req.pk in response["Location"]

    post = {
        "subject": "Another fourth Test-Subject",
        "body": "This is another test body",
        "redirect_url": "http://evil.example.com",
        "publicbody": str(pb.pk),
        "public": True,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    request_sent = reverse("foirequest-request_sent")
    assert request_sent in response["Location"]


@pytest.mark.django_db
def test_redirect_after_request_new_account(world, client, pb):
    pb = PublicBody.objects.all()[0]
    mail.outbox = []
    redirect_url = "/foo/?blub=bla"
    post = {
        "subject": "Another Third Test-Subject",
        "body": "This is another test body",
        "redirect_url": redirect_url,
        "publicbody": str(pb.pk),
        "public": True,
        "private": True,
        "first_name": "Stefan",
        "last_name": "Wehrmeyer",
        "address": "TestStreet 3\n55555 Town",
        "user_email": "sw@example.com",
        "reference": "foo:bar",
        "terms": "on",
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302
    account_new = reverse("account-new")
    assert account_new in response["Location"]

    req = FoiRequest.objects.get(title=post["subject"])
    message = mail.outbox[0]
    assert message.to[0] == post["user_email"]
    match = re.search(r"http://[\w:]+(/[\w/]+/\d+/\w+/\S*)", message.body)
    assert match is not None
    url = match.group(1)
    response = client.get(url)
    assert "/foo/?" in response["Location"]
    assert "blub=bla" in response["Location"]
    assert "ref=foo%3Abar" in response["Location"]
    assert "request=%s" % req.pk in response["Location"]


@pytest.mark.django_db
def test_foi_email_settings(world, client, pb, settings):
    pb = PublicBody.objects.all()[0]
    client.login(email="dummy@example.org", password="froide")
    post = {
        "subject": "Another Third Test-Subject",
        "body": "This is another test body",
        "publicbody": str(pb.pk),
        "law": str(pb.default_law.pk),
        "public": True,
    }

    def email_func(username, secret):
        return "email+%s@foi.example.com" % username

    settings.FOI_EMAIL_FIXED_FROM_ADDRESS = False
    settings.FOI_EMAIL_TEMPLATE = email_func

    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302
    req = FoiRequest.objects.get(title=post["subject"])
    assert req.messages[0].sent
    addr = email_func(req.user.username, "")
    assert req.secret_address == addr


@pytest.mark.django_db
def test_logged_in_request_no_public_body(world, client, pb):
    client.login(email="dummy@example.org", password="froide")
    user = User.objects.get(email="dummy@example.org")
    req = factories.FoiRequestFactory.create(
        user=user, status=FoiRequest.STATUS.PUBLICBODY_NEEDED, public_body=None
    )
    factories.FoiMessageFactory.create(request=req, sent=False)
    pb = PublicBody.objects.all()[0]

    other_req = FoiRequest.objects.filter(public_body__isnull=False)[0]
    response = client.post(
        reverse(
            "foirequest-suggest_public_body", kwargs={"slug": req.slug + "garbage"}
        ),
        {"publicbody": str(pb.pk)},
    )
    assert response.status_code == 404
    response = client.post(
        reverse("foirequest-suggest_public_body", kwargs={"slug": other_req.slug}),
        {"publicbody": str(pb.pk)},
    )
    assert response.status_code == 400
    response = client.post(
        reverse("foirequest-suggest_public_body", kwargs={"slug": req.slug}), {}
    )
    assert response.status_code == 400
    response = client.post(
        reverse("foirequest-suggest_public_body", kwargs={"slug": req.slug}),
        {"publicbody": "9" * 10},
    )
    assert response.status_code == 400
    client.logout()
    client.login(email="info@fragdenstaat.de", password="froide")
    mail.outbox = []
    response = client.post(
        reverse("foirequest-suggest_public_body", kwargs={"slug": req.slug}),
        {"publicbody": str(pb.pk), "reason": "A good reason"},
    )
    assert response.status_code == 302
    assert [t.public_body for t in req.publicbodysuggestion_set.all()] == [pb]
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to[0] == req.user.email
    response = client.post(
        reverse("foirequest-suggest_public_body", kwargs={"slug": req.slug}),
        {"publicbody": str(pb.pk), "reason": "A good reason"},
    )
    assert response.status_code == 302
    assert [t.public_body for t in req.publicbodysuggestion_set.all()] == [pb]
    assert len(mail.outbox) == 1

    # set public body
    response = client.post(
        reverse("foirequest-set_public_body", kwargs={"slug": req.slug + "garbage"}),
        {"suggestion": str(pb.pk)},
    )
    assert response.status_code == 404
    client.logout()
    client.login(email="dummy@example.org", password="froide")
    response = client.post(
        reverse("foirequest-set_public_body", kwargs={"slug": req.slug}), {}
    )
    assert response.status_code == 400
    req = FoiRequest.objects.get(pk=req.pk)
    assert req.public_body is None

    response = client.post(
        reverse("foirequest-set_public_body", kwargs={"slug": req.slug}),
        {"suggestion": "9" * 10},
    )
    assert response.status_code == 400
    client.logout()
    response = client.post(
        reverse("foirequest-set_public_body", kwargs={"slug": req.slug}),
        {"suggestion": str(pb.pk)},
    )
    assert_forbidden(response)
    client.login(email="dummy@example.org", password="froide")
    response = client.post(
        reverse("foirequest-set_public_body", kwargs={"slug": req.slug}),
        {"suggestion": str(pb.pk)},
    )
    assert response.status_code == 302
    req = FoiRequest.objects.get(pk=req.pk)
    message = req.foimessage_set.all()[0]
    assert req.law.letter_start in message.plaintext
    assert req.law.letter_end in message.plaintext
    assert req.public_body == pb
    response = client.post(
        reverse("foirequest-set_public_body", kwargs={"slug": req.slug}),
        {"suggestion": str(pb.pk)},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_postal_reply(world, client, pb):
    client.login(email="info@fragdenstaat.de", password="froide")
    pb = PublicBody.objects.all()[0]
    post = {
        "subject": "Totally Random Request",
        "body": "This is another test body",
        "publicbody": str(pb.pk),
        "public": True,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302
    req = FoiRequest.objects.get(title=post["subject"])
    response = client.get(reverse("foirequest-show", kwargs={"slug": req.slug}))
    assert response.status_code == 200
    # Date message back
    message = req.foimessage_set.all()[0]
    message.timestamp = datetime(2011, 1, 1, 0, 0, 0, tzinfo=dt_timezone.utc)
    message.save()
    req.created_at = message.timestamp
    req.save()

    file_size = os.path.getsize(factories.TEST_PDF_PATH)
    post = QueryDict(mutable=True)
    post.update(
        {
            "postal_reply-date": "3000-01-01",  # far future
            "postal_reply-sender": "Some Sender",
            "postal_reply-subject": "",
            "postal_reply-text": "Some Text",
        }
    )

    client.logout()
    response = client.post(
        reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
    )
    assert_forbidden(response)
    client.login(email="info@fragdenstaat.de", password="froide")

    pb = req.public_body
    req.public_body = None
    req.save()
    response = client.post(
        reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 400
    req.public_body = pb
    req.save()

    response = client.post(
        reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 400
    post["postal_reply-date"] = "01/41garbl"
    response = client.post(
        reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
    )
    assert "postal_reply_form" in response.context
    assert response.status_code == 400
    # Reply cant be send before request start data
    post["postal_reply-date"] = "2010-31-11"
    response = client.post(
        reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
    )
    assert "postal_reply_form" in response.context
    assert response.status_code == 400
    # Reply date must be a valid date
    post["postal_reply-date"] = "2011-01-02"
    post["postal_reply-publicbody"] = str(pb.pk)
    post["postal_reply-text"] = ""
    with open(factories.TEST_PDF_PATH, "rb") as f:
        post["postal_reply-files"] = f
        response = client.post(
            reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
        )
    assert response.status_code == 302

    message = req.foimessage_set.all()[1]

    attachment = message.foiattachment_set.all()[0]
    assert attachment.file.size == file_size
    assert attachment.size == file_size
    assert attachment.name == "test.pdf"

    # Change name in order to upload it again
    attachment.name = "other_test.pdf"
    attachment.save()

    postal_attachment_form = message.get_postal_attachment_form()
    assert postal_attachment_form

    post = QueryDict(mutable=True)

    post_var = postal_attachment_form.add_prefix("files")

    with open(factories.TEST_PDF_PATH, "rb") as f:
        post.update({post_var: f})
        response = client.post(
            reverse(
                "foirequest-add_postal_reply_attachment",
                kwargs={"slug": req.slug, "message_id": "9" * 5},
            ),
            post,
        )

    assert response.status_code == 404

    client.logout()
    with open(factories.TEST_PDF_PATH, "rb") as f:
        post.update({post_var: f})
        response = client.post(
            reverse(
                "foirequest-add_postal_reply_attachment",
                kwargs={"slug": req.slug, "message_id": message.pk},
            ),
            post,
        )
    assert_forbidden(response)

    client.login(email="dummy@example.org", password="froide")
    with open(factories.TEST_PDF_PATH, "rb") as f:
        post.update({post_var: f})
        response = client.post(
            reverse(
                "foirequest-add_postal_reply_attachment",
                kwargs={"slug": req.slug, "message_id": message.pk},
            ),
            post,
        )

    assert response.status_code == 403

    client.logout()
    client.login(email="info@fragdenstaat.de", password="froide")
    message = req.foimessage_set.all()[0]

    with open(factories.TEST_PDF_PATH, "rb") as f:
        post.update({post_var: f})
        response = client.post(
            reverse(
                "foirequest-add_postal_reply_attachment",
                kwargs={"slug": req.slug, "message_id": message.pk},
            ),
            post,
        )

    assert response.status_code == 400

    message = req.foimessage_set.all()[1]
    response = client.post(
        reverse(
            "foirequest-add_postal_reply_attachment",
            kwargs={"slug": req.slug, "message_id": message.pk},
        )
    )
    assert response.status_code == 400

    with open(factories.TEST_PDF_PATH, "rb") as f:
        post.update({post_var: f})
        response = client.post(
            reverse(
                "foirequest-add_postal_reply_attachment",
                kwargs={"slug": req.slug, "message_id": message.pk},
            ),
            post,
        )

    assert response.status_code == 302
    assert len(message.foiattachment_set.all()) == 2

    # Adding the same document again will add another with a numbered filename
    with open(factories.TEST_PDF_PATH, "rb") as f:
        post.update({post_var: f})
        response = client.post(
            reverse(
                "foirequest-add_postal_reply_attachment",
                kwargs={"slug": req.slug, "message_id": message.pk},
            ),
            post,
        )

    assert response.status_code == 302
    attachments = {att.name for att in message.foiattachment_set.all()}
    assert len(attachments) == 3
    assert "test_1.pdf" in attachments
    assert "test.pdf" in attachments


@pytest.mark.django_db
def test_set_message_sender(world, client, pb, msgobj):
    from froide.foirequest.forms import get_message_sender_form

    mail.outbox = []
    client.login(email="dummy@example.org", password="froide")
    pb = PublicBody.objects.all()[0]
    post = {
        "subject": "A simple test request",
        "body": "This is another test body",
        "publicbody": str(pb.id),
        "public": True,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302
    assert len(mail.outbox) == 2
    req = FoiRequest.objects.get(title=post["subject"])
    add_message_from_email(
        req,
        ParsedEmail(
            msgobj,
            **{
                "date": timezone.now() + timedelta(days=1),
                "subject": "Re: %s" % req.title,
                "body": """Message""",
                "html": None,
                "from_": EmailAddress("FoI Officer", "randomfoi@example.com"),
                "to": [EmailAddress(req.user.get_full_name(), req.secret_address)],
                "cc": [],
                "resent_to": [],
                "resent_cc": [],
                "attachments": [],
            },
        ),
    )
    req = FoiRequest.objects.get(title=post["subject"])
    assert len(req.messages) == 2
    assert len(mail.outbox) == 3
    notification = mail.outbox[-1]
    match = re.search(
        r"https?://[^/]+(/.*?/%d/[^\s]+)" % req.user.pk, notification.body
    )
    assert match is not None
    url = match.group(1)
    client.logout()
    response = client.get(reverse("account-show"))
    assert response.status_code == 302
    response = client.get(url)
    assert response.status_code == 200
    response = client.post(url)
    assert response.status_code == 302
    message = req.messages[1]
    assert req.get_absolute_short_url() in response["Location"]
    response = client.get(reverse("account-requests"))
    assert response.status_code == 200
    form = get_message_sender_form(foimessage=message)
    post_var = form.add_prefix("sender")
    assert message.is_response
    original_pb = req.public_body
    alternate_pb = PublicBody.objects.all()[1]
    response = client.post(
        reverse(
            "foirequest-set_message_sender",
            kwargs={"slug": req.slug, "message_id": "9" * 8},
        ),
        {post_var: alternate_pb.id},
    )
    assert response.status_code == 404
    assert message.sender_public_body != alternate_pb

    client.logout()
    response = client.post(
        reverse(
            "foirequest-set_message_sender",
            kwargs={"slug": req.slug, "message_id": str(message.pk)},
        ),
        {post_var: alternate_pb.id},
    )
    assert_forbidden(response)
    assert message.sender_public_body != alternate_pb

    client.logout()
    client.login(email="dummy@example.org", password="froide")
    mes = req.messages[0]
    response = client.post(
        reverse(
            "foirequest-set_message_sender",
            kwargs={"slug": req.slug, "message_id": str(mes.pk)},
        ),
        {post_var: str(alternate_pb.id)},
    )
    assert response.status_code == 400
    assert message.sender_public_body != alternate_pb

    response = client.post(
        reverse(
            "foirequest-set_message_sender",
            kwargs={"slug": req.slug, "message_id": message.pk},
        ),
        {post_var: "9" * 5},
    )
    assert response.status_code == 400
    assert message.sender_public_body != alternate_pb

    response = client.post(
        reverse(
            "foirequest-set_message_sender",
            kwargs={"slug": req.slug, "message_id": message.pk},
        ),
        {post_var: str(alternate_pb.id)},
    )
    assert response.status_code == 302
    message = FoiMessage.objects.get(pk=message.pk)
    assert message.sender_public_body == alternate_pb

    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(
        reverse(
            "foirequest-set_message_sender",
            kwargs={"slug": req.slug, "message_id": str(message.pk)},
        ),
        {post_var: original_pb.id},
    )
    assert response.status_code == 403
    assert message.sender_public_body != original_pb


@pytest.mark.django_db
def test_apply_moderation(world, client):
    req = FoiRequest.objects.all()[0]
    assert req.is_foi
    response = client.post(
        reverse("foirequest-apply_moderation", kwargs={"slug": req.slug + "-blub"}),
        data={"moderation_trigger": "nonfoi"},
    )
    assert response.status_code == 302

    client.login(email="dummy@example.org", password="froide")
    response = client.post(
        reverse("foirequest-apply_moderation", kwargs={"slug": req.slug + "-blub"}),
        data={"moderation_trigger": "nonfoi"},
    )
    assert response.status_code == 404

    response = client.post(
        reverse("foirequest-apply_moderation", kwargs={"slug": req.slug}),
        data={"moderation_trigger": "nonfoi"},
    )
    assert response.status_code == 403

    req = FoiRequest.objects.get(pk=req.pk)
    assert req.is_foi
    client.logout()
    client.login(email="moderator@example.org", password="froide")
    response = client.post(
        reverse("foirequest-apply_moderation", kwargs={"slug": req.slug}),
        data={"moderation_trigger": "nonfoi"},
    )
    assert response.status_code == 302
    req = FoiRequest.objects.get(pk=req.pk)
    assert not req.is_foi


@pytest.mark.django_db
def test_mark_not_foi_perm(world, client):
    req = FoiRequest.objects.all()[0]
    user = User.objects.get(email="dummy@example.org")
    content_type = ContentType.objects.get_for_model(FoiRequest)
    permission = Permission.objects.get(
        codename="mark_not_foi",
        content_type=content_type,
    )

    user.user_permissions.add(permission)

    assert req.is_foi

    client.login(email="dummy@example.org", password="froide")
    response = client.post(
        reverse("foirequest-apply_moderation", kwargs={"slug": req.slug}),
        data={"moderation_trigger": "nonfoi"},
    )
    assert response.status_code == 302
    req = FoiRequest.objects.get(pk=req.pk)
    assert not req.is_foi


@pytest.mark.django_db
def test_escalation_message(world, client):
    req = FoiRequest.objects.all()[0]
    attachments = list(generate_foirequest_files(req))
    req._messages = None  # Reset messages cache
    response = client.post(
        reverse("foirequest-escalation_message", kwargs={"slug": req.slug + "blub"})
    )
    assert response.status_code == 404
    response = client.post(
        reverse("foirequest-escalation_message", kwargs={"slug": req.slug})
    )
    assert_forbidden(response)
    ok = client.login(email="dummy@example.org", password="froide")
    assert ok
    response = client.post(
        reverse("foirequest-escalation_message", kwargs={"slug": req.slug})
    )
    assert response.status_code == 403
    client.logout()
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(
        reverse("foirequest-escalation_message", kwargs={"slug": req.slug})
    )
    assert response.status_code == 400
    mail.outbox = []
    response = client.post(
        reverse("foirequest-escalation_message", kwargs={"slug": req.slug}),
        {
            "subject": "My Escalation Subject",
            "message": ("My Escalation Message" "\n%s\nDone" % req.get_auth_link()),
        },
    )
    assert response.status_code == 302
    assert req.get_absolute_url() in response["Location"]
    assert req.law.mediator == req.messages[-1].recipient_public_body
    assert req.get_auth_link() not in req.messages[-1].plaintext_redacted
    assert len(mail.outbox) == 2
    message = list(filter(lambda x: x.to[0] == req.law.mediator.email, mail.outbox))[-1]
    assert message.attachments[0][0] == "_%s.pdf" % req.pk
    assert message.attachments[0][2] == "application/pdf"
    assert len(message.attachments) == len(attachments)
    assert [x[0] for x in message.attachments] == [x[0] for x in attachments]


@pytest.mark.django_db
def test_set_tags(world, client):
    req = FoiRequest.objects.all()[0]

    # Bad method
    response = client.get(reverse("foirequest-set_tags", kwargs={"slug": req.slug}))
    assert response.status_code == 405

    # Bad slug
    response = client.post(
        reverse("foirequest-set_tags", kwargs={"slug": req.slug + "blub"})
    )
    assert response.status_code == 404

    # Not logged in
    client.logout()
    response = client.post(reverse("foirequest-set_tags", kwargs={"slug": req.slug}))
    assert_forbidden(response)

    # Not staff
    client.login(email="dummy@example.org", password="froide")
    response = client.post(reverse("foirequest-set_tags", kwargs={"slug": req.slug}))
    assert response.status_code == 403

    # Bad form
    client.logout()
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(reverse("foirequest-set_tags", kwargs={"slug": req.slug}))
    assert response.status_code == 302
    assert len(req.tags.all()) == 0

    response = client.post(
        reverse("foirequest-set_tags", kwargs={"slug": req.slug}),
        {"tags": 'SomeTag, "Another Tag", SomeTag'},
    )
    assert response.status_code == 302
    tags = req.tags.all()
    assert len(tags) == 2
    assert "SomeTag" in [t.name for t in tags]
    assert "Another Tag" in [t.name for t in tags]


@pytest.mark.django_db
def test_set_summary(world, client):
    req = FoiRequest.objects.all()[0]

    # Bad method
    response = client.get(reverse("foirequest-set_summary", kwargs={"slug": req.slug}))
    assert response.status_code == 405

    # Bad slug
    response = client.post(
        reverse("foirequest-set_summary", kwargs={"slug": req.slug + "blub"})
    )
    assert response.status_code == 404

    # Not logged in
    client.logout()
    response = client.post(reverse("foirequest-set_summary", kwargs={"slug": req.slug}))
    assert_forbidden(response)

    # Not user of request
    client.login(email="dummy@example.org", password="froide")
    response = client.post(reverse("foirequest-set_summary", kwargs={"slug": req.slug}))
    assert response.status_code == 403

    # Request not final
    client.logout()
    client.login(email="info@fragdenstaat.de", password="froide")
    req.status = "awaiting_response"
    req.save()
    response = client.post(reverse("foirequest-set_summary", kwargs={"slug": req.slug}))
    assert response.status_code == 400

    # No resolution given
    req.status = FoiRequest.STATUS.RESOLVED
    req.save()
    response = client.post(reverse("foirequest-set_summary", kwargs={"slug": req.slug}))
    assert response.status_code == 400

    res = "This is resolved"
    response = client.post(
        reverse("foirequest-set_summary", kwargs={"slug": req.slug}),
        {"summary": res},
    )
    assert response.status_code == 302
    req = FoiRequest.objects.get(id=req.id)
    assert req.summary == res


@pytest.mark.django_db
def test_approve_attachment(world, client):
    req = FoiRequest.objects.all()[0]
    mes = req.messages[-1]
    att = factories.FoiAttachmentFactory.create(belongs_to=mes, approved=False)

    # Bad method
    response = client.get(
        reverse(
            "foirequest-approve_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 405

    # Bad slug
    response = client.post(
        reverse(
            "foirequest-approve_attachment",
            kwargs={"slug": req.slug + "blub", "attachment_id": att.id},
        )
    )
    assert response.status_code == 404

    # Not logged in
    client.logout()
    response = client.post(
        reverse(
            "foirequest-approve_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert_forbidden(response)

    # Not user of request
    client.login(email="dummy@example.org", password="froide")
    response = client.post(
        reverse(
            "foirequest-approve_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 403
    client.logout()

    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(
        reverse(
            "foirequest-approve_attachment",
            kwargs={"slug": req.slug, "attachment_id": "9" * 8},
        )
    )
    assert response.status_code == 404

    user = User.objects.get(username="sw")
    user.is_staff = False
    user.save()

    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(
        reverse(
            "foirequest-approve_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 302
    att = FoiAttachment.objects.get(id=att.id)
    assert att.approved

    att.approved = False
    att.can_approve = False
    att.save()
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(
        reverse(
            "foirequest-approve_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 403
    att = FoiAttachment.objects.get(id=att.id)
    assert not att.approved
    assert not att.can_approve

    client.logout()
    client.login(email="dummy_staff@example.org", password="froide")
    response = client.post(
        reverse(
            "foirequest-approve_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 302
    att = FoiAttachment.objects.get(id=att.id)
    assert att.approved
    assert not att.can_approve


@pytest.mark.django_db
def test_delete_attachment(world, client):
    from froide.foirequest.models.attachment import DELETE_TIMEFRAME

    now = timezone.now()

    req = FoiRequest.objects.all()[0]
    mes = req.messages[-1]
    att = factories.FoiAttachmentFactory.create(
        belongs_to=mes, approved=False, timestamp=now
    )

    # Bad method
    response = client.get(
        reverse(
            "foirequest-delete_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 405

    # Bad slug
    response = client.post(
        reverse(
            "foirequest-delete_attachment",
            kwargs={"slug": req.slug + "blub", "attachment_id": att.id},
        )
    )
    assert response.status_code == 404

    # Not logged in
    client.logout()
    response = client.post(
        reverse(
            "foirequest-delete_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert_forbidden(response)

    # Not user of request
    client.login(email="dummy@example.org", password="froide")
    response = client.post(
        reverse(
            "foirequest-delete_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 403
    client.logout()

    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(
        reverse(
            "foirequest-delete_attachment",
            kwargs={"slug": req.slug, "attachment_id": "9" * 8},
        )
    )
    assert response.status_code == 404

    user = User.objects.get(username="sw")
    user.is_staff = False
    user.save()

    client.login(email="info@fragdenstaat.de", password="froide")

    # Don't allow deleting from non-postal messages
    mes.kind = "email"
    mes.save()
    response = client.post(
        reverse(
            "foirequest-delete_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 403
    att_exists = FoiAttachment.objects.filter(id=att.id).exists()
    assert att_exists

    mes.kind = "post"
    mes.save()

    att.can_approve = False
    att.save()

    response = client.post(
        reverse(
            "foirequest-delete_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 403
    att_exists = FoiAttachment.objects.filter(id=att.id).exists()
    assert att_exists

    att.can_approve = True
    att.save()

    response = client.post(
        reverse(
            "foirequest-delete_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 302
    att_exists = FoiAttachment.objects.filter(id=att.id).exists()
    assert not att_exists

    att = factories.FoiAttachmentFactory.create(
        belongs_to=mes, approved=False, timestamp=now - DELETE_TIMEFRAME
    )

    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(
        reverse(
            "foirequest-delete_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 403
    att = FoiAttachment.objects.get(id=att.id)

    att = factories.FoiAttachmentFactory.create(
        belongs_to=mes, approved=False, timestamp=now
    )

    client.logout()
    client.login(email="dummy_staff@example.org", password="froide")
    response = client.post(
        reverse(
            "foirequest-delete_attachment",
            kwargs={"slug": req.slug, "attachment_id": att.id},
        )
    )
    assert response.status_code == 302
    att_exists = FoiAttachment.objects.filter(id=att.id).exists()
    assert not att_exists


@pytest.mark.django_db
def test_make_same_request(world, client):
    req = FoiRequest.objects.all()[0]

    # req doesn't exist
    response = client.post(
        reverse("foirequest-make_same_request", kwargs={"slug": req.slug + "blub"})
    )
    assert response.status_code == 404

    # message is publishable
    response = client.post(
        reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
    )
    assert response.status_code == 302

    req.not_publishable = True
    req.save()

    # not loged in, no form
    response = client.get(reverse("foirequest-show", kwargs={"slug": req.slug}))
    assert response.status_code == 200

    mail.outbox = []
    user = User.objects.get(username="dummy")
    response = client.post(
        reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
    )
    assert response.status_code == 400
    assert len(mail.outbox) == 0
    assert FoiRequest.objects.filter(same_as=req, user=user).count() == 0

    # user made original request
    client.login(email="info@fragdenstaat.de", password="froide")

    response = client.post(
        reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
    )
    assert response.status_code == 400

    req.same_as_count = 12000
    req.save()

    # make request
    client.logout()
    client.login(email="dummy@example.org", password="froide")
    response = client.post(
        reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
    )
    assert response.status_code == 302
    assert len(mail.outbox) == 2
    same_req = FoiRequest.objects.get(same_as=req, user=user)
    assert same_req.slug.endswith("-12001")
    assert same_req.get_absolute_url() in response["Location"]
    assert list(req.same_as_set) == [same_req]
    assert same_req.identical_count() == 1
    req = FoiRequest.objects.get(pk=req.pk)
    assert req.identical_count() == 1

    response = client.post(
        reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
    )
    assert response.status_code == 400
    same_req = FoiRequest.objects.get(same_as=req, user=user)

    client.logout()
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(
        reverse("foirequest-make_same_request", kwargs={"slug": same_req.slug})
    )
    assert response.status_code == 400

    client.logout()
    mail.outbox = []
    post = {
        "first_name": "Bob",
        "last_name": "Bobbington",
        "address": "MyAddres 12\nB-Town",
        "user_email": "bob@example.com",
        "terms": "on",
        "public": True,
        "private": True,
    }
    response = client.post(
        reverse("foirequest-make_same_request", kwargs={"slug": same_req.slug}),
        post,
    )
    assert response.status_code == 302
    assert FoiRequest.objects.filter(same_as=req).count() == 2
    same_req2 = FoiRequest.objects.get(same_as=req, user__email=post["user_email"])
    assert same_req2.status == "awaiting_user_confirmation"
    assert same_req2.visibility == 0
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to[0] == post["user_email"]
    match = re.search(r"/(\d+)/(\w+)/", message.body)
    assert match is not None
    new_user = User.objects.get(id=int(match.group(1)))
    assert not new_user.is_active
    secret = match.group(2)
    response = client.get(
        reverse(
            "account-confirm",
            kwargs={"user_id": new_user.pk, "secret": secret},
        )
    )
    assert response.status_code == 302
    new_user = User.objects.get(id=new_user.pk)
    assert new_user.is_active
    same_req2 = FoiRequest.objects.get(pk=same_req2.pk)
    assert same_req2.status == "awaiting_response"
    assert same_req2.visibility == 2
    assert len(mail.outbox) == 3


@pytest.mark.django_db
def test_empty_costs(world, client):
    req = FoiRequest.objects.all()[0]
    user = User.objects.get(username="sw")
    req.status = "awaits_classification"
    req.user = user
    req.save()
    factories.FoiMessageFactory.create(status=None, request=req)
    client.login(email="info@fragdenstaat.de", password="froide")
    status = "awaiting_response"
    response = client.post(
        reverse("foirequest-set_status", kwargs={"slug": req.slug}),
        {"status": status, "costs": "", "resolution": ""},
    )
    assert response.status_code == 302
    req = FoiRequest.objects.get(pk=req.pk)
    assert req.costs == Decimal(0.0)
    assert req.status == status


@pytest.mark.django_db
def test_resolution(world, client):
    req = FoiRequest.objects.all()[0]
    user = User.objects.get(username="sw")
    req.status = "awaits_classification"
    req.user = user
    req.save()
    mes = factories.FoiMessageFactory.create(status=None, request=req)
    client.login(email="info@fragdenstaat.de", password="froide")
    status = FoiRequest.STATUS.RESOLVED
    response = client.post(
        reverse("foirequest-set_status", kwargs={"slug": req.slug}),
        {"status": status, "costs": "", "resolution": ""},
    )
    assert response.status_code == 400
    response = client.post(
        reverse("foirequest-set_status", kwargs={"slug": req.slug}),
        {"status": status, "costs": "", "resolution": "bogus"},
    )
    assert response.status_code == 400
    response = client.post(
        reverse("foirequest-set_status", kwargs={"slug": req.slug}),
        {
            "status": status,
            "costs": "",
            "resolution": FoiRequest.RESOLUTION.SUCCESSFUL,
        },
    )
    assert response.status_code == 302
    req = FoiRequest.objects.get(pk=req.pk)
    assert req.costs == Decimal(0.0)
    assert req.status == FoiRequest.STATUS.RESOLVED
    assert req.resolution == FoiRequest.RESOLUTION.SUCCESSFUL
    assert req.days_to_resolution() == (mes.timestamp - req.created_at).days


@pytest.mark.django_db
def test_search(world, client, pb):
    pb = PublicBody.objects.all()[0]
    factories.rebuild_index()
    response = client.get("%s?q=%s" % (reverse("foirequest-search"), pb.name[:6]))
    assert response.status_code == 302
    assert quote(pb.name[:6]) in response["Location"]


@pytest.mark.django_db
def test_full_text_request(world, client, pb):
    client.login(email="dummy@example.org", password="froide")
    pb = PublicBody.objects.all()[0]
    law = pb.default_law
    post = {
        "subject": "A Public Body Request",
        "body": "This is another test body with Ümläut€n",
        "full_text": "true",
        "publicbody": str(pb.id),
        "public": True,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302
    req = FoiRequest.objects.get(title=post["subject"])
    message = req.foimessage_set.all()[0]
    assert post["body"] in message.plaintext
    assert post["body"] in message.plaintext_redacted
    assert law.letter_start not in message.plaintext
    assert law.letter_start not in message.plaintext_redacted
    assert law.letter_end not in message.plaintext
    assert law.letter_end not in message.plaintext_redacted


@pytest.mark.django_db
def test_redaction_config(world, client, msgobj):
    client.login(email="dummy@example.org", password="froide")
    req = FoiRequest.objects.all()[0]
    name = "Petra Radetzky"
    add_message_from_email(
        req,
        ParsedEmail(
            msgobj,
            **{
                "date": timezone.now(),
                "subject": "Reply",
                "body": (
                    "Guten Tag,\nblub\nbla\n\n" "Mit freundlichen Grüßen\n" + name
                ),
                "html": "html",
                "from_": EmailAddress(name, "petra.radetsky@bund.example.org"),
                "to": [EmailAddress("", req.secret_address)],
                "cc": [],
                "resent_to": [],
                "resent_cc": [],
                "attachments": [],
            },
        ),
    )
    req = FoiRequest.objects.all()[0]
    last = req.messages[-1]
    assert name not in last.plaintext_redacted
    form = get_send_message_form(
        {
            "sendmessage-to": req.public_body.email,
            "sendmessage-subject": "Testing",
            "sendmessage-address": "Address",
            "sendmessage-message": (
                "Sehr geehrte Frau radetzky,"
                "\n\nblub\n\nMit freundlichen Grüßen"
                "\nStefan Wehrmeyer"
            ),
        },
        foirequest=req,
    )
    assert form.is_valid()
    form.save()

    req = FoiRequest.objects.all()[0]
    last = req.messages[-1]
    assert "radetzky" not in last.plaintext_redacted


@pytest.mark.django_db
def test_redaction_urls(world):
    from froide.foirequest.utils import redact_plaintext_with_request

    req = FoiRequest.objects.all()[0]
    url1 = "https://example.org/request/1231/upload/abcdef0123456789"
    url2 = "https://example.org/r/1231/auth/abcdef0123456789"
    url3 = "https://example.org/request/1231/auth/abcdef0123456789"
    plaintext = """Testing
        Really{url1}
        !!{url2}
        {url3}#also
    """.format(url1=url1, url2=url2, url3=url3)
    assert url1 in plaintext
    assert url2 in plaintext
    assert url3 in plaintext

    redacted = redact_plaintext_with_request(plaintext, req)
    assert url1 not in redacted
    assert url2 not in redacted
    assert url3 not in redacted


@pytest.mark.django_db
def test_empty_pb_email(world, client, pb):
    client.login(email="info@fragdenstaat.de", password="froide")
    pb = PublicBody.objects.all()[0]
    pb.email = ""
    pb.save()
    response = client.get(
        reverse("foirequest-make_request", kwargs={"publicbody_slug": pb.slug})
    )
    assert response.status_code == 404
    post = {
        "subject": "Test-Subject",
        "body": "This is a test body",
        "publicbody": str(pb.pk),
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 400
    post = {
        "subject": "Test-Subject",
        "body": "This is a test body",
        "publicbody": str(pb.pk),
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 400
    assert "publicbody" in response.context["publicbody_form"].errors
    assert len(response.context["publicbody_form"].errors) == 1


@mock.patch(
    "froide.foirequest.views.attachment.redact_attachment_task.delay",
    lambda a, b, c: None,
)
@pytest.mark.django_db
def test_redact_attachment(world, client):
    foirequest = FoiRequest.objects.all()[0]
    message = foirequest.messages[0]
    att = factories.FoiAttachmentFactory.create(belongs_to=message)
    url = reverse(
        "foirequest-redact_attachment",
        kwargs={"slug": foirequest.slug, "attachment_id": "8" * 5},
    )

    assert att.name in repr(att)

    response = client.get(url)
    assert_forbidden(response)

    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.get(url)
    assert response.status_code == 404

    url = reverse(
        "foirequest-redact_attachment",
        kwargs={"slug": foirequest.slug, "attachment_id": str(att.id)},
    )
    response = client.get(url)
    assert response.status_code == 200

    response = client.post(url, "[]", content_type="application/json")
    assert response.status_code == 200

    old_att = FoiAttachment.objects.get(id=att.id)
    assert not old_att.can_approve
    # Redaction happens in background task, mocked away
    new_att = old_att.redacted
    assert new_att.is_redacted
    assert not new_att.approved
    assert new_att.file == ""


@pytest.mark.django_db
def test_extend_deadline(world, client):
    foirequest = FoiRequest.objects.all()[0]
    old_due_date = foirequest.due_date
    url = reverse("foirequest-extend_deadline", kwargs={"slug": foirequest.slug})
    post = {"time": ""}

    response = client.post(url, post)
    assert_forbidden(response)

    client.login(email="dummy@example.org", password="froide")
    response = client.post(url, post)
    assert response.status_code == 403

    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(url, post)
    assert response.status_code == 400

    response = client.post(url, {"time": 1000})
    assert response.status_code == 400
    response = client.post(url, {"time": -10})
    assert response.status_code == 400

    post = {"time": "2"}
    response = client.post(url, post)
    assert response.status_code == 302
    foirequest = FoiRequest.objects.get(id=foirequest.id)
    assert foirequest.due_date == foirequest.law.calculate_due_date(old_due_date, 2)


@pytest.mark.django_db
def test_resend_message(world, client):
    foirequest = FoiRequest.objects.all()[0]
    message = foirequest.messages[0]
    message.save()
    url = reverse(
        "foirequest-resend_message",
        kwargs={"slug": foirequest.slug, "message_id": message.id},
    )

    response = client.post(url)
    assert_forbidden(response)

    client.login(email="dummy@example.org", password="froide")
    response = client.post(url)
    assert response.status_code == 403

    client.login(email="moderator@example.org", password="froide")
    response = client.post(url)
    assert response.status_code == 404

    DeliveryStatus.objects.create(
        message=message, status=DeliveryStatus.Delivery.STATUS_BOUNCED
    )
    assert message.can_resend_bounce

    response = client.post(url)
    assert response.status_code == 302
    message = FoiMessage.objects.get(id=message.pk)
    ds = message.get_delivery_status()
    assert ds.status == DeliveryStatus.Delivery.STATUS_SENDING


@pytest.mark.django_db
def test_approve_message(world, client):
    foirequest = FoiRequest.objects.all()[0]
    message = foirequest.messages[0]
    message.content_hidden = True
    message.save()
    url = reverse(
        "foirequest-approve_message",
        kwargs={"slug": foirequest.slug, "message_id": message.pk},
    )

    response = client.post(url)
    assert_forbidden(response)

    client.login(email="dummy@example.org", password="froide")
    response = client.post(url)
    assert response.status_code == 403

    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.post(url)
    assert response.status_code == 302

    message = FoiMessage.objects.get(pk=message.pk)
    assert not message.content_hidden


@pytest.mark.django_db
def test_too_long_subject(world, client, pb):
    client.login(email="info@fragdenstaat.de", password="froide")
    pb = PublicBody.objects.all()[0]
    post = {
        "subject": "Test" * 64,
        "body": "This is another test body with Ümläut€n",
        "publicbody": pb.pk,
        "public": True,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 400

    post = {
        "subject": "Test" * 55 + " a@b.de",
        "body": "This is another test body with Ümläut€n",
        "publicbody": pb.pk,
        "public": True,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302


@pytest.mark.django_db
def test_remove_double_numbering(world, client, pb, msgobj):
    req = FoiRequest.objects.all()[0]
    form = get_send_message_form(
        {
            "sendmessage-to": req.public_body.email,
            "sendmessage-subject": req.title + " [#%s]" % req.pk,
            "sendmessage-message": "Test",
            "sendmessage-address": "Address",
        },
        foirequest=req,
    )
    assert form.is_valid()
    form.save()
    req = FoiRequest.objects.all()[0]
    last = req.messages[-1]
    assert last.subject.count("[#%s]" % req.pk) == 1


@override_settings(FOI_EMAIL_FIXED_FROM_ADDRESS=False)
@pytest.mark.django_db
def test_user_name_phd():
    from froide.helper.email_utils import make_address

    from_addr = make_address("j.doe.12345@example.org", "John Doe, Dr.")
    assert from_addr == '"John Doe, Dr." <j.doe.12345@example.org>'


@pytest.fixture
def request_throttle(settings):
    settings.FROIDE_CONFIG = copy.deepcopy(settings.FROIDE_CONFIG)
    settings.FROIDE_CONFIG["request_throttle"] = [(2, 60), (5, 60 * 60)]


@pytest.mark.django_db
def test_throttling(world, client, pb, request_throttle):
    pb = PublicBody.objects.all()[0]
    client.login(email="dummy@example.org", password="froide")

    post = {
        "subject": "Another Third Test-Subject",
        "body": "This is another test body",
        "publicbody": str(pb.pk),
        "public": True,
    }
    post["law"] = str(pb.default_law.pk)

    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302

    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302

    response = client.post(reverse("foirequest-make_request"), post)

    assertContains(
        response,
        "exceeded your request limit of 2 requests in 1",
        status_code=400,
    )
    assertContains(
        response,
        '<a href="{}">'.format(get_content_url("throttled")),
        status_code=400,
    )


@pytest.mark.django_db
def test_throttling_same_as(world, client, request_throttle):
    requests = []
    for i in range(3):
        requests.append(
            factories.FoiRequestFactory(
                slug="same-as-request-%d" % i, not_publishable=True
            )
        )

    client.login(email="dummy@example.org", password="froide")

    for i, req in enumerate(requests):
        response = client.post(
            reverse("foirequest-make_same_request", kwargs={"slug": req.slug})
        )
        if i < 2:
            assert response.status_code == 302

    assertContains(
        response,
        "exceeded your request limit of 2 requests in 1\xa0minute.",
        status_code=400,
    )


@pytest.mark.django_db
def test_blocked_address(world):
    from froide.account.models import AccountBlocklist

    AccountBlocklist.objects.create(
        name="Address block test", address="Test(-| )Str 5.+Testtown"
    )
    req = FoiRequest.objects.all()[0]

    def make_form():
        return get_send_message_form(
            {
                "sendmessage-to": req.public_body.email,
                "sendmessage-subject": req.title,
                "sendmessage-message": "Test",
                "sendmessage-address": "Test-Str 5\nTesttown",
            },
            foirequest=req,
        )

    form = make_form()
    assert form.is_valid()

    # Set request user to normal user
    req.user = User.objects.get(email="dummy@example.org")
    form = make_form()
    assert not form.is_valid()
    assert "address" in form.errors


@pytest.mark.django_db
def test_invalid_emails_not_shown_in_reply(world, client, msgobj):
    client.login(email="dummy@example.org", password="froide")
    req = FoiRequest.objects.all()[0]
    valid_email = "valid-email@example.org"
    invalid_email = "invalid-email to address"
    add_message_from_email(
        req,
        ParsedEmail(
            msgobj,
            **{
                "from_": EmailAddress("from", "from@ddress.example.org"),
                "to": [
                    EmailAddress("", valid_email),
                    EmailAddress("", invalid_email),
                ],
                "date": timezone.now(),
                "subject": "Reply",
                "body": "Content",
                "html": "html",
                "cc": [],
                "resent_to": [],
                "resent_cc": [],
                "attachments": [],
            },
        ),
    )

    req = FoiRequest.objects.all()[0]
    reply_addresses = possible_reply_addresses(req)
    reply_emails_adresses = [x[1] for x in reply_addresses]
    assert valid_email in reply_emails_adresses
    assert invalid_email not in reply_emails_adresses

    form = get_send_message_form(foirequest=req)
    form_reply_addresses = form.fields["to"].choices
    form_reply_emails_adresses = [x[1] for x in form_reply_addresses]
    assert valid_email in form_reply_emails_adresses
    assert invalid_email not in form_reply_emails_adresses


@pytest.mark.django_db
def test_attachment_wrapping(world, client):
    req = FoiRequest.objects.all()[0]
    msg = factories.FoiMessageFactory.create(status=None, request=req)
    for _ in range(3):
        factories.FoiAttachmentFactory.create(belongs_to=msg, approved=True)
    response = client.get(req.get_absolute_url())
    assertNotContains(response, "more attachments")
    factories.FoiAttachmentFactory.create(belongs_to=msg, approved=True)
    response = client.get(req.get_absolute_url())
    assertNotContains(response, "more attachments")
    factories.FoiAttachmentFactory.create(belongs_to=msg, approved=True)
    response = client.get(req.get_absolute_url())
    assertContains(response, "Show 2 more attachments")


@pytest.mark.django_db
def test_hiding_content(world, msgobj):
    req = FoiRequest.objects.all()[0]
    mediator = req.law.mediator
    form = get_escalation_message_form(
        {"subject": "Escalate", "message": "Content"}, foirequest=req
    )
    assert form.is_valid()
    form.save()
    req = FoiRequest.objects.all()[0]
    add_message_from_email(
        req,
        ParsedEmail(
            msgobj,
            **{
                "date": timezone.now(),
                "subject": "Reply",
                "body": "Content",
                "html": "html",
                "from_": EmailAddress("Name", mediator.email),
                "to": [EmailAddress("", req.secret_address)],
                "cc": [],
                "resent_to": [],
                "resent_cc": [],
                "attachments": [],
            },
        ),
    )
    req = FoiRequest.objects.all()[0]
    last = req.messages[-1]
    assert last.content_hidden


@pytest.mark.django_db
def test_no_public_body(world, client):
    user = User.objects.get(username="sw")
    req = factories.FoiRequestFactory.create(
        user=user, public_body=None, status="public_body_needed", site=world
    )
    req.save()
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.get(req.get_absolute_url())
    assertNotContains(response, "Mediation")
    response = client.post(
        reverse("foirequest-escalation_message", kwargs={"slug": req.slug})
    )
    assert response.status_code == 400
    message = list(response.context["messages"])[0]
    assert "cannot be escalated" in message.message


@pytest.fixture
def pb(world):
    return PublicBody.objects.filter(jurisdiction__slug="nrw")[0]


@pytest.mark.django_db
def test_letter_public_body(world, client, pb):
    client.login(email="info@fragdenstaat.de", password="froide")
    post = {
        "subject": "Jurisdiction-Test-Subject",
        "body": "This is a test body",
        "publicbody": pb.pk,
        "public": True,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302
    req = FoiRequest.objects.get(title="Jurisdiction-Test-Subject")
    law = FoiLaw.objects.get(meta=True, jurisdiction__slug="nrw")
    assert req.law == law
    mes = req.messages[0]
    assert law.letter_end in mes.plaintext


@pytest.mark.django_db
def test_package(world):
    fr = FoiRequest.objects.all()[0]
    bytes = package_foirequest(fr)
    zfile = zipfile.ZipFile(BytesIO(bytes), "r")
    filenames = [
        "%s/_%s.pdf" % (fr.pk, fr.pk),
        "%s/%s.pdf" % (fr.pk, fr.messages[0].timestamp.date().isoformat()),
        "%s/%s.pdf" % (fr.pk, fr.messages[1].timestamp.date().isoformat()),
        r"%s/%s-file_\d+.pdf" % (fr.pk, fr.messages[1].timestamp.date().isoformat()),
        r"%s/%s-file_\d+.pdf" % (fr.pk, fr.messages[1].timestamp.date().isoformat()),
    ]
    zip_names = zfile.namelist()
    assert len(filenames) == len(zip_names)
    for zname, fname in zip(zip_names, filenames, strict=False):
        assert bool(re.match(r"^%s$" % fname, zname))


@pytest.mark.django_db
def test_postal_after_last(world, client, pb, faker):
    """
    Test that the postal upload sets the datetime of the uploaded message *after* the last message
    that already exists on that day
    """

    with time_machine.travel(datetime(2011, 1, 1, 15, 00, 00), tick=False):
        client.login(email="info@fragdenstaat.de", password="froide")
        pb = PublicBody.objects.all()[0]
        post = {
            "subject": "Totally Random Request",
            "body": "This is another test body",
            "publicbody": str(pb.pk),
            "public": True,
        }
        response = client.post(reverse("foirequest-make_request"), post)
        assert response.status_code == 302
        req = FoiRequest.objects.get(title=post["subject"])
        response = client.get(reverse("foirequest-show", kwargs={"slug": req.slug}))
        assert response.status_code == 200
        message = req.foimessage_set.all()[0]

    with time_machine.travel(datetime(2011, 1, 2, 10, 00, 00), tick=False):
        post = QueryDict(mutable=True)
        msg_text = faker.text()
        post.update(
            {
                "postal_reply-date": "2011-01-01",
                "postal_reply-sender": "Some Sender",
                "postal_reply-subject": "",
                "postal_reply-text": msg_text,
                "postal_reply-publicbody": str(pb.pk),
            }
        )
        response = client.post(
            reverse("foirequest-add_postal_reply", kwargs={"slug": req.slug}), post
        )
        assert response.status_code == 302

    msg_queryset = req.foimessage_set.filter(plaintext=msg_text)
    assert msg_queryset.count() == 1
    created_msg = msg_queryset.get()
    assert created_msg.timestamp > message.timestamp
    assert created_msg.timestamp.date() == date(2011, 1, 1)
    message = req.foimessage_set.all()[1]


@pytest.mark.django_db
@pytest.mark.no_delivery_mock
def test_mail_confirmation_after_success(world, user, client, faker):
    pb = PublicBody.objects.first()
    foirequest_post = {
        "subject": faker.text(max_nb_chars=50),
        "body": faker.text(max_nb_chars=500),
        "publicbody": pb.pk,
        "public": True,
    }

    client.login(email=user.email, password="froide")
    response = client.post(reverse("foirequest-make_request"), foirequest_post)
    assert response.status_code == 302
    req = FoiRequest.objects.filter(
        user=user, public_body=foirequest_post["publicbody"]
    ).get()
    assert req.title == foirequest_post["subject"]
    assert req.description == foirequest_post["body"]

    # Test that we queue the email for the public body
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert mail.outbox[0].to[0] == pb.email
    assert foirequest_post["body"] in message.body

    # Now mark the email as sent
    foimessage = req.foimessage_set.get()

    email_left_queue.send(
        sender=__name__,
        to=foimessage.recipient_email,
        from_address=foimessage.sender_email,
        message_id=foimessage.email_message_id,
        status="sent",
        log=[],
    )

    # Expectation: The user should receive a confirmation that the request was sent
    assert len(mail.outbox) == 2
    confirmation_message = mail.outbox[1]
    assert (
        "Your Freedom of Information Request was sent" in confirmation_message.subject
    )

    # Action: Send a new foimessage in the request
    foimessage: FoiMessage = factories.FoiMessageFactory(
        request=req,
        subject=faker.text(max_nb_chars=50),
        kind=MessageKind.EMAIL,
        is_response=False,
        sender_user=user,
        sender_name=user.display_name(),
        sender_email=req.secret_address,
        recipient_email=req.public_body.email,
        recipient_public_body=req.public_body,
        recipient=req.public_body.name,
        plaintext=faker.text(max_nb_chars=50),
    )
    foimessage.send()

    # Expectation: The message is send to the public body
    assert len(mail.outbox) == 3
    message = mail.outbox[2]
    assert message.to[0] == pb.email
    assert foimessage.plaintext in message.body

    # Action: Mark the email as sent
    email_left_queue.send(
        sender=__name__,
        to=foimessage.recipient_email,
        from_address=foimessage.sender_email,
        message_id=foimessage.email_message_id,
        status="sent",
        log=[],
    )

    # Expectation: The user should receive a confirmation that the message was sent
    assert len(mail.outbox) == 4
    confirmation_message = mail.outbox[3]
    assert "Your message was sent" in confirmation_message.subject

    # Action: Mark the email as sent *again*
    email_left_queue.send(
        sender=__name__,
        to=foimessage.recipient_email,
        from_address=foimessage.sender_email,
        message_id=foimessage.email_message_id,
        status="sent",
        log=[],
    )

    # Expectation: The user should not receive another confirmation that the message was sent
    assert len(mail.outbox) == 4


@pytest.mark.django_db
def test_request_body_leading_indent(world, client, pb):
    ok = client.login(email="info@fragdenstaat.de", password="froide")
    assert ok

    user = User.objects.get(username="sw")
    user.organization_name = "ACME Org"
    user.save()

    pb = PublicBody.objects.all()[0]
    post = {
        "subject": "Test-Subject",
        "body": "  1. Indented\n  2. Indented",
        "publicbody": pb.pk,
        "public": True,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302

    req = FoiRequest.objects.filter(user=user, public_body=pb).order_by("-id")[0]
    foi_message = req.foimessage_set.all()[0]
    assert post["body"] in foi_message.plaintext
    assert len(mail.outbox) == 2
    message = mail.outbox[0]
    assert post["body"] in message.body
