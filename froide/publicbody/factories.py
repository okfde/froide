import random
import string
from datetime import timedelta

from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.utils import timezone

import factory
from factory.django import DjangoModelFactory

from froide.account.factories import UserFactory

from .models import (
    Category,
    Classification,
    FoiLaw,
    Jurisdiction,
    PublicBody,
    PublicBodyTag,
)


def random_name(num=10):
    return "".join([random.choice(string.ascii_lowercase) for _ in range(num)])


class JurisdictionFactory(DjangoModelFactory):
    class Meta:
        model = Jurisdiction

    name = factory.Sequence(lambda n: "Jurisdiction {0}".format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = ""
    hidden = False
    rank = factory.Sequence(lambda n: n)


class PublicBodyTagFactory(DjangoModelFactory):
    class Meta:
        model = PublicBodyTag

    name = factory.Sequence(lambda n: "Public Body Tag {0}".format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: "Category {0}".format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    depth = 1
    path = factory.Sequence(lambda n: Category._get_path(None, 1, n))


class ClassificationFactory(DjangoModelFactory):
    class Meta:
        model = Classification

    name = factory.Sequence(lambda n: "Classification {0}".format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    depth = 1
    path = factory.Sequence(lambda n: Classification._get_path(None, 1, n))


class PublicBodyFactory(DjangoModelFactory):
    class Meta:
        model = PublicBody

    name = factory.Sequence(lambda n: "Pübli€ Body {0}".format(random_name()))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = ""
    url = "http://example.com"
    parent = None
    root = None
    depth = 0

    classification = factory.SubFactory(ClassificationFactory)

    email = factory.Sequence(lambda n: "pb-{0}@{0}.example.com".format(n))
    contact = "Some contact stuff"
    address = "An address"
    website_dump = ""
    request_note = ""

    _created_by = factory.SubFactory(UserFactory)
    _updated_by = factory.SubFactory(UserFactory)
    confirmed = True

    number_of_requests = 0
    site = factory.LazyAttribute(lambda o: Site.objects.get(id=1))

    jurisdiction = factory.SubFactory(JurisdictionFactory)


class FoiLawFactory(DjangoModelFactory):
    class Meta:
        model = FoiLaw

    name = factory.Sequence(lambda n: "FoiLaw {0}".format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = "Description"
    long_description = "Long description"
    created = timezone.now() - timedelta(days=600)
    updated = timezone.now() - timedelta(days=300)
    meta = False
    letter_start = factory.Sequence(lambda n: "Dear Sir or Madam, {0}".format(n))
    letter_end = factory.LazyAttribute(
        lambda o: "Requesting according to {0}.\n\n Regards\nUsername".format(o.name)
    )
    jurisdiction = factory.SubFactory(JurisdictionFactory)
    priority = 3
    url = "http://example.com"
    max_response_time = 1
    max_response_time_unit = "month_de"
    refusal_reasons = "No way\nNo say"
    mediator = None
    email_only = False

    site = factory.LazyAttribute(lambda o: Site.objects.get(id=1))
