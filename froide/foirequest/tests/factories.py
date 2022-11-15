import base64
import os
import random
import string
import time
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.utils import timezone

import factory
from elasticsearch.exceptions import RequestError
from factory.django import DjangoModelFactory

from froide.account.factories import UserFactory
from froide.helper.text_utils import slugify
from froide.publicbody.factories import (
    CategoryFactory,
    FoiLawFactory,
    JurisdictionFactory,
    PublicBodyFactory,
    PublicBodyTagFactory,
)

from ..models import (
    DeferredMessage,
    FoiAttachment,
    FoiEvent,
    FoiMessage,
    FoiProject,
    FoiRequest,
    PublicBodySuggestion,
    RequestDraft,
)

TEST_PDF_URL = "test.pdf"
TEST_PDF_PATH = os.path.join(settings.MEDIA_ROOT, TEST_PDF_URL)


class FoiRequestFactory(DjangoModelFactory):
    class Meta:
        model = FoiRequest

    title = factory.Sequence(lambda n: "My FoiRequest Number {0}".format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.title))
    description = factory.Sequence(lambda n: "Desc {0}".format(n))
    resolution = ""
    public_body = factory.LazyAttribute(lambda o: PublicBodyFactory())
    public = True
    status = ""
    visibility = 2
    user = factory.LazyAttribute(lambda o: UserFactory())
    created_at = timezone.now() - timedelta(days=14)
    last_message = timezone.now() - timedelta(days=2)
    resolved_on = None
    due_date = timezone.now() + timedelta(days=14)

    secret_address = factory.LazyAttribute(
        lambda o: "%s.%s@fragdenstaat.de"
        % (
            o.user.username,
            "".join([random.choice(string.hexdigits) for x in range(8)]),
        )
    )
    secret = ""
    same_as = None
    same_as_count = 0

    law = factory.SubFactory(FoiLawFactory)

    costs = 0.0
    refusal_reason = ""
    checked = True
    is_foi = True

    jurisdiction = factory.SubFactory(JurisdictionFactory)

    site = factory.LazyAttribute(lambda o: Site.objects.get(id=1))


class RequestDraftFactory(DjangoModelFactory):
    class Meta:
        model = RequestDraft

    user = factory.LazyAttribute(lambda o: UserFactory())
    subject = factory.Sequence(lambda n: "My FoiRequest Number {0}".format(n))
    body = factory.Sequence(lambda n: "My FoiRequest Body Number {0}".format(n))


class FoiProjectFactory(DjangoModelFactory):
    class Meta:
        model = FoiProject

    user = factory.LazyAttribute(lambda o: UserFactory())
    title = factory.Sequence(lambda n: "My FoiProject Number {0}".format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.title))


class DeferredMessageFactory(DjangoModelFactory):
    class Meta:
        model = DeferredMessage

    recipient = factory.Sequence(lambda n: "blub{}@fragdenstaat.de".format(n))
    timestamp = timezone.now() - timedelta(hours=1)
    request = None
    mail = factory.LazyAttribute(
        lambda o: base64.b64encode(
            b"To: <"
            + o.recipient.encode("ascii")
            + b""">
Subject: Latest Improvements
Date: Mon, 5 Jul 2010 07:54:40 +0200

Test"""
        ).decode("ascii")
    )


class PublicBodySuggestionFactory(DjangoModelFactory):
    class Meta:
        model = PublicBodySuggestion


class FoiMessageFactory(DjangoModelFactory):
    class Meta:
        model = FoiMessage

    request = factory.SubFactory(FoiRequestFactory)

    sent = True
    is_response = factory.LazyAttribute(lambda o: not o.sender_user)
    is_escalation = False
    sender_user = None
    sender_email = "sender@example.com"
    sender_name = "Sender name"
    sender_public_body = factory.SubFactory(PublicBodyFactory)

    recipient = "Recipient name"
    recipient_email = "recipient@example.com"
    recipient_public_body = None
    status = "awaiting_response"

    timestamp = factory.Sequence(
        lambda n: timezone.now() - timedelta(days=1000 - int(n))
    )
    subject = "subject"
    subject_redacted = "subject"
    plaintext = "plaintext"
    plaintext_redacted = "plaintext"
    html = ""
    redacted = False
    not_publishable = False


class FoiAttachmentFactory(DjangoModelFactory):
    class Meta:
        model = FoiAttachment

    belongs_to = factory.SubFactory(FoiMessageFactory)
    name = factory.Sequence(lambda n: "file_{0}.pdf".format(n))
    file = TEST_PDF_URL
    size = 500
    filetype = "application/pdf"
    format = "pdf"
    can_approve = True
    approved = True


class FoiEventFactory(DjangoModelFactory):
    class Meta:
        model = FoiEvent

    request = factory.SubFactory(FoiRequestFactory)
    user = None
    public_body = None
    public = True
    event_name = "became_overdue"
    timestamp = factory.Sequence(lambda n: timezone.now() - timedelta(days=n))
    context = "{}"


def make_world() -> Site:
    site = Site.objects.get(id=1)

    user1 = UserFactory.create(
        is_staff=True,
        username="sw",
        email="info@fragdenstaat.de",
        first_name="Stefan",
        last_name="Wehrmeyer",
        address="DummyStreet23\n12345 Town",
    )
    UserFactory.create(
        is_staff=True,
        is_superuser=True,
        username="supersw",
        email="superuser@fragdenstaat.de",
        first_name="Stefan",
        last_name="Wehrmeyer",
        address="DummyStreet23\n12345 Town",
    )
    UserFactory.create(
        username="dummy", email="dummy@example.org", first_name="Dummy", last_name="D."
    )
    moderator = UserFactory.create(
        username="moderator",
        email="moderator@example.org",
        first_name="Mod",
        last_name="Erator",
    )
    moderator_pii = UserFactory.create(
        username="moderator_pii",
        email="moderator_pii@example.org",
        first_name="Mod",
        last_name="Erator PII",
    )
    dummy_staff = UserFactory.create(
        is_staff=True,
        username="dummy_staff",
        email="dummy_staff@example.org",
    )
    content_type = ContentType.objects.get_for_model(FoiRequest)
    change_permission = Permission.objects.get(
        codename="change_foirequest",
        content_type=content_type,
    )
    dummy_staff.user_permissions.add(change_permission)

    moderate_permission = Permission.objects.get(
        codename="moderate",
        content_type=content_type,
    )
    moderate_pii_permission = Permission.objects.get(
        codename="moderate_pii",
        content_type=content_type,
    )

    moderator.user_permissions.add(moderate_permission)
    moderator_pii.user_permissions.add(moderate_permission)
    moderator_pii.user_permissions.add(moderate_pii_permission)

    bund = JurisdictionFactory.create(name="Bund")
    nrw = JurisdictionFactory.create(name="NRW")

    topic_1 = CategoryFactory.create(is_topic=True)
    topic_2 = CategoryFactory.create(is_topic=True)

    tag_1 = PublicBodyTagFactory.create(is_topic=True)
    tag_2 = PublicBodyTagFactory.create(is_topic=True)

    mediator_bund = PublicBodyFactory.create(jurisdiction=bund, site=site)
    mediator_bund.categories.add(topic_1)

    ifg_bund = FoiLawFactory.create(
        site=site, jurisdiction=bund, name="IFG Bund", mediator=mediator_bund
    )
    uig_bund = FoiLawFactory.create(
        site=site, jurisdiction=bund, name="UIG Bund", mediator=mediator_bund
    )
    meta_bund = FoiLawFactory.create(
        site=site,
        jurisdiction=bund,
        meta=True,
        name="IFG-UIG Bund",
        mediator=mediator_bund,
        pk=10000,
    )
    mediator_bund.laws.add(ifg_bund, uig_bund, meta_bund)
    meta_bund.combined.add(ifg_bund, uig_bund)
    ifg_nrw = FoiLawFactory.create(site=site, jurisdiction=nrw, name="IFG NRW")
    uig_nrw = FoiLawFactory.create(site=site, jurisdiction=nrw, name="UIG NRW")
    meta_nrw = FoiLawFactory.create(
        site=site, jurisdiction=nrw, name="IFG-UIG NRW", meta=True
    )
    meta_nrw.combined.add(ifg_nrw, uig_nrw)

    for _ in range(5):
        pb_bund_1 = PublicBodyFactory.create(jurisdiction=bund, site=site)
        pb_bund_1.categories.add(topic_1)
        pb_bund_1.tags.add(tag_1)
        pb_bund_1.laws.add(ifg_bund, uig_bund, meta_bund)
    for _ in range(5):
        pb_nrw_1 = PublicBodyFactory.create(jurisdiction=nrw, site=site)
        pb_nrw_1.categories.add(topic_2)
        pb_nrw_1.tags.add(tag_2)
        pb_nrw_1.laws.add(ifg_nrw, uig_nrw, meta_nrw)
    req = FoiRequestFactory.create(
        site=site, user=user1, jurisdiction=bund, law=meta_bund, public_body=pb_bund_1
    )
    FoiMessageFactory.create(
        request=req, sender_user=user1, recipient_public_body=pb_bund_1
    )
    mes = FoiMessageFactory.create(request=req, sender_public_body=pb_bund_1)
    FoiAttachmentFactory.create(belongs_to=mes, approved=False)
    FoiAttachmentFactory.create(belongs_to=mes, approved=True)
    return site


def es_retries(func):
    def call_func(*args, **kwargs):
        max_count = 3
        count = 0
        while True:
            try:
                return func(*args, **kwargs)
            except RequestError as e:
                count += 1
                if count <= max_count:
                    time.sleep(2**count)
                    continue
                raise e

    return call_func


@es_retries
def delete_index():
    with open(os.devnull, "a") as f:
        call_command("search_index", action="delete", force=True, stdout=f)


@es_retries
def rebuild_index():
    with open(os.devnull, "a") as f:
        return call_command("search_index", action="rebuild", force=True, stdout=f)
