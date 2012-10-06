# -*- encoding: utf-8 -*-
import csv

from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings
from django.template.defaultfilters import slugify


def csv_reader(f, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(f,
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]


class Command(BaseCommand):
    help = "Loads Hamburg"
    topic_cache = {}

    def handle(self, filepath, *args, **options):
        from django.contrib.auth.models import User
        from django.contrib.sites.models import Site

        from froide.publicbody.models import (PublicBodyTopic, PublicBody,
            Jurisdiction, FoiLaw)

        translation.activate(settings.LANGUAGE_CODE)

        sw = User.objects.get(username='sw')
        site = Site.objects.get_current()
        self.topic_cache = dict([(pb.slug, pb) for pb in PublicBodyTopic.objects.all()])
        juris = Jurisdiction.objects.get(slug='hamburg')

        laws = FoiLaw.objects.filter(jurisdiction=juris)

        fields = ("name", "other_names", "slug", "topic__slug", "classification",
            "depth", "children_count", "email", "description", "url", "website_dump",
            "contact", "address")

        # importing Hamburg
        first = True
        with file(filepath) as f:
            for items in csv_reader(f):
                if first:
                    first = False
                    continue
                items = dict(zip(fields, items))

                topic = self.get_topic(items['topic__slug'])
                classification = items['classification']
                try:
                    PublicBody.objects.get(slug=items['slug'])
                    self.stdout.write((u"Exists %s\n" % items['name']).encode('utf-8'))
                    continue
                except PublicBody.DoesNotExist:
                    pass
                self.stdout.write((u"Trying: %s\n" % items['name']).encode('utf-8'))
                public_body = PublicBody.objects.create(
                    name=items['name'],
                    slug=items['slug'],
                    topic=topic,
                    description=items['description'],
                    url=items['url'],
                    classification=classification,
                    classification_slug=slugify(classification),
                    email=items['email'],
                    contact=items['contact'],
                    address=items['address'],
                    website_dump=items['website_dump'],
                    request_note='',
                    _created_by=sw,
                    _updated_by=sw,
                    confirmed=True,
                    site=site,
                    jurisdiction=juris
                )
                public_body.laws.add(*laws)
                self.stdout.write((u"%s\n" % public_body).encode('utf-8'))

    def get_topic(self, slug):
        return self.topic_cache.get(slug, self.topic_cache['andere'])
