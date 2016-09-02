# -*- encoding: utf-8 -*-
from datetime import datetime, timedelta
import random
import string
import base64
import os

import factory

from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

from froide.publicbody.models import Jurisdiction, FoiLaw, PublicBody, PublicBodyTag
from froide.foirequest.models import (FoiRequest, FoiMessage, FoiAttachment, FoiEvent,
    PublicBodySuggestion, DeferredMessage)


TEST_PDF_URL = "test.pdf"
TEST_PDF_PATH = os.path.join(settings.MEDIA_ROOT, TEST_PDF_URL)


def random_name(num=10):
    return ''.join([random.choice(string.ascii_lowercase) for _ in range(num)])


class SiteFactory(factory.DjangoModelFactory):
    class Meta:
        model = Site

    name = factory.Sequence(lambda n: 'Site %s' % n)
    domain = factory.Sequence(lambda n: 'domain%s.example.com' % n)


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    first_name = 'Jane'
    last_name = factory.Sequence(lambda n: 'D%se' % ('o' * min(20, int(n))))
    username = factory.Sequence(lambda n: 'user_%s' % n)
    email = factory.LazyAttribute(lambda o: '%s.%s@example.org' % (
        o.first_name.lower(), o.last_name.lower()))
    password = factory.PostGenerationMethodCall('set_password', 'froide')
    is_staff = False
    is_active = True
    is_superuser = False
    last_login = datetime(2000, 1, 1).replace(tzinfo=timezone.utc)
    date_joined = datetime(1999, 1, 1).replace(tzinfo=timezone.utc)
    private = False
    address = 'Dummystreet5\n12345 Town'
    organization = ''
    organization_url = ''


class JurisdictionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Jurisdiction

    name = factory.Sequence(lambda n: 'Jurisdiction {0}'.format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = ''
    hidden = False
    rank = factory.Sequence(lambda n: n)


class PublicBodyTagFactory(factory.DjangoModelFactory):
    class Meta:
        model = PublicBodyTag

    name = factory.Sequence(lambda n: 'Public Body Tag {0}'.format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))


class PublicBodyFactory(factory.DjangoModelFactory):
    class Meta:
        model = PublicBody

    name = factory.Sequence(lambda n: u'Pübli€ Body {0}'.format(random_name()))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = ''
    url = 'http://example.com'
    parent = None
    root = None
    depth = 0
    classification = 'Ministry'
    classification_slug = 'ministry'

    email = factory.Sequence(lambda n: 'pb-{0}@{0}.example.com'.format(n))
    contact = 'Some contact stuff'
    address = 'An address'
    website_dump = ''
    request_note = ''

    _created_by = factory.SubFactory(UserFactory)
    _updated_by = factory.SubFactory(UserFactory)
    confirmed = True

    number_of_requests = 0
    site = factory.SubFactory(SiteFactory)

    jurisdiction = factory.SubFactory(JurisdictionFactory)


class FoiLawFactory(factory.DjangoModelFactory):
    class Meta:
        model = FoiLaw

    name = factory.Sequence(lambda n: 'FoiLaw {0}'.format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = 'Description'
    long_description = 'Long description'
    created = timezone.now() - timedelta(days=600)
    updated = timezone.now() - timedelta(days=300)
    meta = False
    letter_start = factory.Sequence(lambda n: 'Dear Sir or Madam, {0}'.format(n))
    letter_end = factory.LazyAttribute(lambda o: 'Requesting according to {0}.\n\n Regards\nUsername'.format(o.name))
    jurisdiction = factory.SubFactory(JurisdictionFactory)
    priority = 3
    url = "http://example.com"
    max_response_time = 1
    max_response_time_unit = 'month_de'
    refusal_reasons = 'No way\nNo say'
    mediator = None
    email_only = False

    site = factory.SubFactory(SiteFactory)


class FoiRequestFactory(factory.DjangoModelFactory):
    class Meta:
        model = FoiRequest

    title = factory.Sequence(lambda n: 'My FoiRequest Number {0}'.format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.title))
    description = factory.Sequence(lambda n: 'Desc {0}'.format(n))
    resolution = ''
    public_body = factory.LazyAttribute(lambda o: PublicBodyFactory())
    public = True
    status = ''
    visibility = 2
    user = factory.LazyAttribute(lambda o: UserFactory())
    first_message = timezone.now() - timedelta(days=14)
    last_message = timezone.now() - timedelta(days=2)
    resolved_on = None
    due_date = timezone.now() + timedelta(days=14)

    secret_address = factory.LazyAttribute(
        lambda o: '%s.%s@fragdenstaat.de' % (o.user.username, ''.join([random.choice(string.hexdigits) for x in range(8)])))
    secret = ''
    same_as = None
    same_as_count = 0

    law = factory.SubFactory(FoiLawFactory)

    costs = 0.0
    refusal_reason = ""
    checked = True
    is_foi = True

    jurisdiction = factory.SubFactory(JurisdictionFactory)

    site = factory.SubFactory(SiteFactory)


class DeferredMessageFactory(factory.DjangoModelFactory):
    class Meta:
        model = DeferredMessage

    recipient = factory.Sequence(lambda n: 'blub%s@fragdenstaat.de'.format(n))
    timestamp = timezone.now() - timedelta(hours=1)
    request = None
    mail = factory.LazyAttribute(lambda o:
        base64.b64encode(b'To: <' + o.recipient.encode('ascii') + b'''>
Subject: Latest Improvements
Date: Mon, 5 Jul 2010 07:54:40 +0200

Test'''))


class PublicBodySuggestionFactory(factory.DjangoModelFactory):
    class Meta:
        model = PublicBodySuggestion


class FoiMessageFactory(factory.DjangoModelFactory):
    class Meta:
        model = FoiMessage

    request = factory.SubFactory(FoiRequestFactory)

    sent = True
    is_response = factory.LazyAttribute(lambda o: not o.sender_user)
    is_postal = False
    is_escalation = False
    sender_user = None
    sender_email = 'sender@example.com'
    sender_name = 'Sender name'
    sender_public_body = factory.SubFactory(PublicBodyFactory)

    recipient = 'Recipient name'
    recipient_email = 'recipient@example.com'
    recipient_public_body = None
    status = 'awaiting_response'

    timestamp = factory.Sequence(
        lambda n: timezone.now() - timedelta(days=1000 - int(n))
    )
    subject = 'subject'
    subject_redacted = 'subject'
    plaintext = 'plaintext'
    plaintext_redacted = 'plaintext'
    html = ''
    original = 'E-mailOriginal'
    redacted = False
    not_publishable = False


class FoiAttachmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = FoiAttachment

    belongs_to = factory.SubFactory(FoiMessageFactory)
    name = factory.Sequence(lambda n: "file_{0}.pdf".format(n))
    file = TEST_PDF_URL
    size = 500
    filetype = 'application/pdf'
    format = 'pdf'
    can_approve = True
    approved = True


class FoiEventFactory(factory.DjangoModelFactory):
    class Meta:
        model = FoiEvent

    request = factory.SubFactory(FoiRequestFactory)
    user = None
    public_body = None
    public = True
    event_name = 'became_overdue'
    timestamp = factory.Sequence(lambda n: timezone.now() - timedelta(days=n))
    context_json = '{}'


def make_world():
    site = Site.objects.get(id=1)

    user1 = UserFactory.create(is_staff=True, username='sw',
        email='mail@stefanwehrmeyer.com',
        first_name='Stefan', last_name='Wehrmeyer',
        address='DummyStreet23\n12345 Town')
    UserFactory.create(username='dummy', first_name='Dummy', last_name='D.')
    UserFactory.create(is_staff=True, username='dummy_staff')
    bund = JurisdictionFactory.create(name='Bund')
    nrw = JurisdictionFactory.create(name='NRW')

    topic_1 = PublicBodyTagFactory.create(is_topic=True)
    topic_2 = PublicBodyTagFactory.create(is_topic=True)

    mediator_bund = PublicBodyFactory.create(jurisdiction=bund, site=site)
    mediator_bund.tags.add(topic_1)

    ifg_bund = FoiLawFactory.create(site=site, jurisdiction=bund,
        name='IFG Bund',
        mediator=mediator_bund
    )
    uig_bund = FoiLawFactory.create(site=site, jurisdiction=bund,
        name='UIG Bund',
        mediator=mediator_bund
    )
    meta_bund = FoiLawFactory.create(site=site, jurisdiction=bund,
        meta=True,
        name='IFG-UIG Bund',
        mediator=mediator_bund,
        pk=10000
    )
    mediator_bund.laws.add(ifg_bund, uig_bund, meta_bund)
    meta_bund.combined.add(ifg_bund, uig_bund)
    ifg_nrw = FoiLawFactory.create(site=site, jurisdiction=nrw, name='IFG NRW')
    uig_nrw = FoiLawFactory.create(site=site, jurisdiction=nrw, name='UIG NRW')
    meta_nrw = FoiLawFactory.create(site=site, jurisdiction=nrw, name='IFG-UIG NRW',
        meta=True)
    meta_nrw.combined.add(ifg_nrw, uig_nrw)

    for _ in range(5):
        pb_bund_1 = PublicBodyFactory.create(jurisdiction=bund, site=site)
        pb_bund_1.tags.add(topic_1)
        pb_bund_1.laws.add(ifg_bund, uig_bund, meta_bund)
    for _ in range(5):
        pb_nrw_1 = PublicBodyFactory.create(jurisdiction=nrw, site=site)
        pb_nrw_1.tags.add(topic_2)
        pb_nrw_1.laws.add(ifg_nrw, uig_nrw, meta_nrw)
    req = FoiRequestFactory.create(site=site, user=user1, jurisdiction=bund,
        law=meta_bund, public_body=pb_bund_1)
    FoiMessageFactory.create(request=req, sender_user=user1,
                             recipient_public_body=pb_bund_1)
    mes = FoiMessageFactory.create(request=req, sender_public_body=pb_bund_1)
    FoiAttachmentFactory.create(belongs_to=mes, approved=False)
    FoiAttachmentFactory.create(belongs_to=mes, approved=True)
    return site


def rebuild_index():
    from haystack import connections
    from haystack.constants import DEFAULT_ALIAS

    from django.core.management import call_command

    connections[DEFAULT_ALIAS].get_backend().clear()
    call_command('update_index')
