# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings
from django.template.defaultfilters import slugify


class Command(BaseCommand):
    help = "Loads Berlin"
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
        juris = Jurisdiction.objects.get(slug='berlin')

        laws = FoiLaw.objects.filter(jurisdiction=juris)

        # importing Berlin
        with file(filepath) as f:
            first = True
            for line in f:
                if first:
                    first = False
                    continue
                line = line.decode('utf-8')
                href, rest = line.split(',', 1)
                name, email = rest.rsplit(',', 1)
                if name.startswith('"') and name.endswith('"'):
                    name = name[1:-1]
                if not href:
                    href = None
                if not email:
                    email = None
                topic = self.get_topic(name)
                classification = self.get_classification(name)
                try:
                    PublicBody.objects.get(slug=slugify(name))
                    continue
                except PublicBody.DoesNotExist:
                    pass
                self.stdout.write((u"Trying: %s\n" % name).encode('utf-8'))
                public_body = PublicBody.objects.create(
                    name=name,
                    slug=slugify(name),
                    topic=topic,
                    description="",
                    url=href,
                    classification=classification,
                    classification_slug=slugify(classification),
                    email=email,
                    contact=u'',
                    address=u'',
                    website_dump='',
                    request_note='',
                    _created_by=sw,
                    _updated_by=sw,
                    confirmed=True,
                    site=site,
                    jurisdiction=juris
                )
                public_body.laws.add(*laws)
                self.stdout.write((u"%s\n" % public_body).encode('utf-8'))

    def get_classification(self, name):
        mapping = [u'Gericht', u'Stiftung', u'Kammer', u'Hochschule', u'Universität']
        for m in mapping:
            if m.lower() in name.lower():
                return m
        classifications = name.split()
        if classifications[0].startswith((u'Berliner', u'Der',
                u'Die', u'Das', u'Deutsche',)):
            classification = classifications[1]
        elif classifications[0].startswith((u'Zentrale', u'Staatl',)):
            classification = u" ".join(classifications[:2])
        elif classifications[0].endswith('-'):
            classification = ' '.join(classifications[:3])
        else:
            classification = classifications[0]
        return classification

    def get_topic(self, name):
        name = name.lower()
        mapping = {
            u'gericht': u'justiz',
            u'polizei': u'inneres',
            u'schul': u'bildung-und-forschung',
            u'rechnungs': u'finanzen',
            u'staatsanwaltschaft': u'justiz',
            u'liegenschaftsbetrieb': u'verkehr-und-bau',
            u'hrungshilfe': u'justiz',
            u'finanzamt': u'finanzen',
            u'hrungsaufsichtsstelle': u'justiz',
            u'landwirtschaftskammer': u'landwirtschaft-und-verbraucherschutz',
            u'jugendarrestanstalt': u'justiz',
            u'justiz': u'justiz',
            u'umwelt': u'umwelt',
            u'straßenbau': u'verkehr-und-bau',
            u'wald': u'umwelt',
            u'kriminal': u'inneres',
            u'prüfungsamt': u'bildung-und-forschung'
        }
        for k, v in mapping.items():
            if k in name:
                return self.topic_cache[v]
        return self.topic_cache['andere']
