# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings
from django.template.defaultfilters import slugify


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

        # importing Hamburg
        keys = None
        with file(filepath) as f:
            for line in f:
                line = line.decode('utf-8')
                if keys is None:
                    keys = line.split(',')
                    continue
                items = dict(zip(keys, line.split(',')))
                name = ' '.join([t.capitalize() for t in items['Name'].split(' ')]).strip()
                href = items['Webseite'].strip() or None
                if href and not href.startswith('http'):
                    href = 'http://' + href
                email = items['Email'].lower().strip() or None
                if email and not '@' in email:
                    email = None
                topic = self.get_topic(name)
                classification = items['Klassifikation'] or None
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
                    contact=items['Zustaendiger'],
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
        try:
            return name.split(' ', 1)[0]
        except (ValueError, IndexError):
            return name

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
