from datetime import datetime, timedelta
import random
import string
import base64

import factory

from django.conf import settings
from django.db.models import get_model
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.contrib.auth.models import User
from django.utils import timezone

from froide.account.models import Profile
from froide.publicbody.models import Jurisdiction, FoiLaw, PublicBodyTopic, PublicBody
from froide.foirequest.models import (FoiRequest, FoiMessage, FoiAttachment, FoiEvent,
    PublicBodySuggestion, DeferredMessage)


class SiteFactory(factory.Factory):
    FACTORY_FOR = Site
    name = factory.Sequence(lambda n: 'Site %s' % n)
    domain = factory.Sequence(lambda n: 'domain%s.example.com' % n)


class ProfileFactory(factory.Factory):
    FACTORY_FOR = Profile

    user = None
    private = False
    address = 'Dummystreet5\n12345 Town'


class UserFactory(factory.Factory):
    FACTORY_FOR = User
    first_name = 'Jane'
    last_name = factory.Sequence(lambda n: 'D%se' % ('o' * min(20, int(n))))
    username = factory.Sequence(lambda n: 'user_%s' % n)
    email = factory.LazyAttribute(lambda o: '%s.%s@example.org' % (
        o.first_name.lower(), o.last_name.lower()))
    # password is always 'froide'
    password = 'sha1$20561$8449af959da3f6204acb14f77f1141a114fe55a5'
    is_staff = False
    is_active = True
    is_superuser = False
    last_login = datetime(2000, 1, 1).replace(tzinfo=timezone.utc)
    date_joined = datetime(1999, 1, 1).replace(tzinfo=timezone.utc)
    # profile = factory.RelatedFactory(ProfileFactory, 'user')


def user_create(cls, **kwargs):
    # From https://github.com/votizen/django-factory_boy/blob/master/django_factory_boy/auth.py
    # figure out the profile's related name and strip profile's kwargs
    profile_model, profile_kwargs = None, {}
    try:
        app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
    except (ValueError, AttributeError):
        pass
    else:
        try:
            profile_model = get_model(app_label, model_name)
        except ImportError:
            pass
    if profile_model:
        user_field = profile_model._meta.get_field_by_name('user')[0]
        related_name = user_field.related_query_name()
        profile_prefix = '%s__' % related_name
        for k in kwargs.keys():
            if k.startswith(profile_prefix):
                profile_key = k.replace(profile_prefix, '', 1)
                profile_kwargs[profile_key] = kwargs.pop(k)
    else:
        print "no profile model"
    # create the user
    user = cls._default_manager.create(**kwargs)

    if profile_model and profile_kwargs:
        # update or create the profile model
        profile, created = profile_model._default_manager.get_or_create(
            user=user, defaults=profile_kwargs)
        if not created:
            for k, v in profile_kwargs.items():
                setattr(profile, k, v)
            profile.save()
        setattr(user, related_name, profile)
        setattr(user, '_profile_cache', profile)

    return user
# UserFactory.set_creation_function(user_create)


class JurisdictionFactory(factory.Factory):
    FACTORY_FOR = Jurisdiction

    name = factory.Sequence(lambda n: 'Jurisdiction {0}'.format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = ''
    hidden = False
    rank = factory.Sequence(lambda n: n)


class PublicBodyTopicFactory(factory.Factory):
    FACTORY_FOR = PublicBodyTopic

    name = factory.Sequence(lambda n: 'Public Body Topic {0}'.format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = ''
    count = 5


class PublicBodyFactory(factory.Factory):
    FACTORY_FOR = PublicBody

    name = factory.Sequence(lambda n: 'Public Body {0}'.format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = ''
    topic = factory.SubFactory(PublicBodyTopicFactory)
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


class FoiLawFactory(factory.Factory):
    FACTORY_FOR = FoiLaw

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
    mediator = factory.SubFactory(PublicBodyFactory)
    email_only = False

    site = factory.SubFactory(SiteFactory)


class FoiRequestFactory(factory.Factory):
    FACTORY_FOR = FoiRequest

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


class DeferredMessageFactory(factory.Factory):
    FACTORY_FOR = DeferredMessage

    recipient = factory.Sequence(lambda n: 'blub%s@fragdenstaat.de'.format(n))
    timestamp = timezone.now() - timedelta(hours=1)
    request = None
    mail = factory.LazyAttribute(lambda o:
        base64.b64encode('''To: <%s>
Subject: Latest Improvements
Date: Mon, 5 Jul 2010 07:54:40 +0200

Test'''.format(o.recipient)))


class PublicBodySuggestionFactory(factory.Factory):
    FACTORY_FOR = PublicBodySuggestion


class FoiMessageFactory(factory.Factory):
    FACTORY_FOR = FoiMessage

    request = factory.SubFactory(FoiRequestFactory)

    sent = True
    is_response = True
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

    timestamp = factory.Sequence(lambda n: timezone.now() - timedelta(days=1000 - int(n)))
    subject = 'subject'
    subject_redacted = 'subject'
    plaintext = 'plaintext'
    plaintext_redacted = 'plaintext'
    html = ''
    original = 'E-mailOriginal'
    redacted = False
    not_publishable = False


class FoiAttachmentFactory(factory.Factory):
    FACTORY_FOR = FoiAttachment

    belongs_to = factory.SubFactory(FoiMessageFactory)
    name = factory.Sequence(lambda n: "file_{0}".format(n))
    file = factory.LazyAttribute(lambda o: 'files/foi/{0}/file_{0}.pdf'.format(o.belongs_to.id))
    size = 500
    filetype = 'application/pdf'
    format = 'pdf'
    can_approve = True
    approved = True


class FoiEventFactory(factory.Factory):
    FACTORY_FOR = FoiEvent

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
        first_name='Stefan', last_name='Wehrmeyer')
    p = user1.get_profile()
    p.address = 'DummyStreet23\n12345 Town'
    p.save()
    UserFactory.create(username='dummy', first_name='Dummy', last_name='D.')
    UserFactory.create(is_staff=True, username='dummy_staff')
    bund = JurisdictionFactory.create(name='Bund')
    nrw = JurisdictionFactory.create(name='NRW')
    mediator_bund = PublicBodyFactory.create(jurisdiction=bund, site=site)
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
        pb_bund_1.laws.add(ifg_bund, uig_bund, meta_bund)
    for _ in range(5):
        pb_nrw_1 = PublicBodyFactory.create(jurisdiction=nrw, site=site)
        pb_nrw_1.laws.add(ifg_nrw, uig_nrw, meta_nrw)
    req = FoiRequestFactory.create(site=site, user=user1, jurisdiction=bund,
        law=meta_bund, public_body=pb_bund_1)
    FoiMessageFactory.create(request=req, sender_user=user1, recipient_public_body=pb_bund_1)
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
