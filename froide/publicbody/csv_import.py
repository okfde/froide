import csv
from io import BytesIO, StringIO

import requests

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.utils import timezone

from taggit.utils import parse_tags

from froide.publicbody.models import (
    PublicBody, PublicBodyTag,
    Jurisdiction, Classification, Category
)
from froide.georegion.models import GeoRegion

User = get_user_model()


class CSVImporter(object):
    def __init__(self, user=None):
        if user is None:
            self.user = User.objects.order_by('id')[0]
        else:
            self.user = user
        self.site = Site.objects.get_current()
        self.topic_cache = {}
        self.classification_cache = {}
        self.default_topic = None
        self.jur_cache = {}
        self.category_cache = {}

    def import_from_url(self, url):
        response = requests.get(url)
        # Force requests to evaluate as UTF-8
        response.encoding = 'utf-8'
        csv_file = BytesIO(response.content)
        self.import_from_file(csv_file)

    def import_from_file(self, csv_file):
        """
        csv_file should be encoded in utf-8
        """
        csv_file = StringIO(csv_file.read().decode('utf-8'))
        reader = csv.DictReader(csv_file)
        for row in reader:
            self.import_row(row)

    def import_row(self, row):
        # generate slugs
        if 'name' in row:
            row['name'] = row['name'].strip()

        if 'email' in row:
            row['email'] = row['email'].lower()

        if 'url' in row:
            if row['url'] and not row['url'].startswith(('http://', 'https://')):
                row['url'] = 'http://' + row['url']

        if 'slug' not in row and 'name' in row:
            row['slug'] = slugify(row['name'])

        if 'classification' in row:
            row['classification'] = self.get_classification(row.pop('classification', None))

        categories = parse_tags(row.pop('categories', ''))
        categories = list(self.get_categories(categories))

        tags = parse_tags(row.pop('tags', ''))
        # Backwards compatible handling of topic__slug
        topic_slug = row.pop('topic__slug', None)
        if topic_slug:
            tags.append(self.get_topic(topic_slug))

        # resolve foreign keys
        if 'jurisdiction__slug' in row:
            row['jurisdiction'] = self.get_jurisdiction(row.pop('jurisdiction__slug'))

        region = None
        if 'georegion_id' in row:
            region = self.get_georegion(id=row.pop('georegion_id'))
        elif 'georegion_identifier' in row:
            region = self.get_georegion(
                identifier=row.pop('georegion_identifier')
            )

        parent = row.pop('parent__name', None)
        if parent:
            row['parent'] = PublicBody.objects.get(slug=slugify(parent))

        parent = row.pop('parent__id', None)
        if parent:
            row['parent'] = PublicBody.objects.get(pk=parent)

        # get optional values
        for n in ('description', 'other_names', 'request_note', 'website_dump'):
            if n in row:
                row[n] = row.get(n, '').strip()

        try:
            if 'id' in row and row['id']:
                pb = PublicBody.objects.get(id=row['id'])
            else:
                pb = PublicBody.objects.get(slug=row['slug'])
            # If it exists, update it
            row.pop('id', None)  # Do not update id though
            row.pop('slug', None)  # Do not update slug either
            row['_updated_by'] = self.user
            row['updated_at'] = timezone.now()
            PublicBody.objects.filter(id=pb.id).update(**row)
            pb.laws.clear()
            pb.laws.add(*row['jurisdiction'].laws)
            pb.tags.set(*tags)
            if region:
                pb.regions.add(region)
            pb.categories.set(*categories)
            return pb
        except PublicBody.DoesNotExist:
            pass
        row.pop('id', None)  # Remove id if present
        pb = PublicBody(**row)
        pb._created_by = self.user
        pb._updated_by = self.user
        pb.created_at = timezone.now()
        pb.updated_at = timezone.now()
        pb.confirmed = True
        pb.site = self.site
        pb.save()
        pb.laws.add(*row['jurisdiction'].laws)
        pb.tags.set(*list(tags))
        if region:
            pb.regions.add(region)
        pb.categories.set(*categories)
        return pb

    def get_jurisdiction(self, slug):
        if slug not in self.jur_cache:
            jur = Jurisdiction.objects.get(slug=slug)
            jur.laws = jur.get_all_laws()
            self.jur_cache[slug] = jur
        return self.jur_cache[slug]

    def get_categories(self, cats):
        for cat in cats:
            if cat in self.category_cache:
                yield self.category_cache[cat]
            else:
                category = Category.objects.get(name=cat)
                self.category_cache[cat] = category
                yield category

    def get_georegion(self, id=None, identifier=None, name=None):
        if id is not None:
            return GeoRegion.objects.get(id=id)
        if identifier is not None:
            return GeoRegion.objects.get(region_identifier=identifier)
        return None

    def get_topic(self, slug):
        if slug not in self.topic_cache:
            self.topic_cache[slug] = PublicBodyTag.objects.get(slug=slug, is_topic=True)
        return self.topic_cache[slug]

    def get_classification(self, name):
        if name is None:
            return None
        if name not in self.classification_cache:
            self.classification_cache[name] = Classification.objects.get(name=name)
        return self.classification_cache[name]
