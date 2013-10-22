# -*- encoding: utf-8 -*-
import requests

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.utils.six import StringIO, PY3

if PY3:
    import csv
else:
    import unicodecsv as csv


from froide.publicbody.models import (PublicBody, PublicBodyTopic,
    Jurisdiction, FoiLaw)

User = get_user_model()


class CSVImporter(object):
    topic_cache = {}
    default_topic = None
    jur_cache = {}

    def __init__(self):
        self.user = User.objects.all()[0]
        self.site = Site.objects.get_current()

    def import_from_url(self, url):
        response = requests.get(url)
        # Force requests to evaluate as UTF-8
        response.encoding = 'utf-8'
        self.import_from_file(StringIO(response.text))

    def import_from_file(self, csv_file):
        reader = csv.DictReader(csv_file)
        for row in reader:
            self.import_row(row)

    def import_row(self, row):
        # generate slugs
        row['name'] = row['name'].strip()
        row['email'] = row['email'].lower()
        if row['url'] and not row['url'].startswith(('http://', 'https://')):
            row['url'] = 'http://' + row['url']
        row['slug'] = slugify(row['name'])
        row['classification_slug'] = slugify(row['classification'])

        # resolve foreign keys
        row['topic'] = self.get_topic(row.pop('topic__slug'))
        row['jurisdiction'] = self.get_jurisdiction(row.pop('jurisdiction__slug'))
        parent = row.pop('parent__name', None)
        if parent:
            row['parent'] = PublicBody.objects.get(slug=slugify(parent))

        # get optional values
        for n in ('description', 'other_names', 'request_note', 'website_dump'):
            row[n] = row.get(n, '')

        try:
            if 'id' in row and row['id']:
                pb = PublicBody.objects.get(id=row['id'])
            else:
                pb = PublicBody.objects.get(slug=row['slug'])
            # If it exists, update it
            row.pop('id', None)  # Do not update id though
            row['_updated_by'] = self.user
            PublicBody.objects.filter(id=pb.id).update(**row)
            pb.laws.clear()
            pb.laws.add(*row['jurisdiction'].laws)
            return
        except PublicBody.DoesNotExist:
            pass
        row.pop('id', None)  # Remove id if present
        public_body = PublicBody(**row)
        public_body._created_by = self.user
        public_body._updated_by = self.user
        public_body.confirmed = True
        public_body.site = self.site
        public_body.save()
        public_body.laws.add(*row['jurisdiction'].laws)

    def get_jurisdiction(self, slug):
        if slug not in self.jur_cache:
            jur = Jurisdiction.objects.get(slug=slug)
            laws = FoiLaw.objects.filter(jurisdiction=jur)
            jur.laws = laws
            self.jur_cache[slug] = jur
        return self.jur_cache[slug]

    def get_topic(self, slug):
        if not slug:
            if self.default_topic is None:
                self.default_topic = PublicBodyTopic.objects.all().order_by('-rank', 'id')[0]
            return self.default_topic
        if slug not in self.topic_cache:
            self.topic_cache[slug] = PublicBodyTopic.objects.get(slug=slug)
        return self.topic_cache[slug]
