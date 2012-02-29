# -*- encoding: utf-8 -*-
import os
import json

from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings
from django.template.defaultfilters import slugify


class Command(BaseCommand):
    help = "Counts PulbicBodies for Topics"
    topic_cache = {}

    def handle(self, directory, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)
        from django.contrib.auth.models import User
        sw = User.objects.get(username='sw')
        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        from publicbody.models import PublicBodyTopic
        self.topic_cache = dict([(pb.slug, pb) for pb in PublicBodyTopic.objects.all()])
        from publicbody.models import PublicBody, Jurisdiction, FoiLaw
        juris = Jurisdiction.objects.get(slug='nordrhein-westfalen')

        laws = FoiLaw.objects.filter(jurisdiction=juris)

        # importing landesverwaltung nrw
        with file(os.path.join(directory, 'landesverwaltung_nrw.json')) as f:
            pbs = json.load(f)
            for pb in pbs:
                topic = self.get_topic(pb)
                classifications = pb['name'].split()
                if classifications[0] == 'Der':
                    classification = classifications[1]
                elif classifications[0].startswith('Staatl'):
                    classification = u"Staatliches %s" % classifications[1]
                elif classifications[0].endswith('-'):
                    classification = ' '.join(classifications[:3])
                else:
                    classification = classifications[0]
                try:
                    PublicBody.objects.get(slug=slugify(pb['name']))
                    continue
                except PublicBody.DoesNotExist:
                    pass
                self.stdout.write((u"Trying: %s\n" % pb['name']).encode('utf-8'))
                public_body = PublicBody.objects.create(
                    name=pb['name'],
                    slug=slugify(pb['name']),
                    topic=topic,
                    description="",
                    url=pb.get('web', None),
                    classification=classification,
                    classification_slug=slugify(classification),
                    email=pb.get('email', None),
                    contact="%s\n%s" % (pb.get('kontakt', ''), pb.get('url', '')),
                    address=pb.get('address'),
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

        # importing kommunalverwaltung nrw
        with file(os.path.join(directory, 'kommunalverwaltung_nrw.json')) as f:
            pbs = json.load(f)
            classification = 'Kommunalverwaltung'
            for pb in pbs:
                try:
                    PublicBody.objects.get(slug=slugify(pb['name']))
                    continue
                except PublicBody.DoesNotExist:
                    pass
                name = 'Kommunalverwaltung %s' % pb['name']
                url = None
                if 'url' in pb:
                    url = "http://%s" % pb['url']

                public_body = PublicBody.objects.create(
                    name=name,
                    slug=slugify(name),
                    topic=self.topic_cache['andere'],
                    description="Regierungsbezirk: %s\n%s" % (pb['gov_area'], pb['head']),
                    url=url,
                    classification=classification,
                    classification_slug=slugify(classification),
                    email=pb.get('email', None),
                    contact=u"Telefon: %s\nFax: %s" % (pb.get('phone', ''), pb.get('fax', '')),
                    address=u"%s\n%s %s" % (pb.get('address', ''), pb.get('plz', ''), pb.get('name')),
                    website_dump='',
                    request_note='',
                    _created_by=sw,
                    _updated_by=sw,
                    confirmed=True,
                    site=site,
                    jurisdiction=juris
                )
                public_body.laws.add(*laws)

    def get_topic(self, pb):
        name = pb['name'].lower()
        mapping = {
            'gericht': 'justiz',
            'polizei': 'inneres',
            'schul': 'bildung-und-forschung',
            'rechnungs': 'finanzen',
            'staatsanwaltschaft': 'justiz',
            'liegenschaftsbetrieb': 'verkehr-und-bau',
            'hrungshilfe': 'justiz',
            'finanzamt': 'finanzen',
            'hrungsaufsichtsstelle': 'justiz',
            'landwirtschaftskammer': 'landwirtschaft-und-verbraucherschutz',
            'jugendarrestanstalt': 'justiz',
            'justiz': 'justiz',
            'umwelt': 'umwelt',
            u'straßenbau': 'verkehr-und-bau',
            'wald': 'umwelt',
            'kriminal': 'inneres',
            u'prüfungsamt': 'bildung-und-forschung'
        }
        for k, v in mapping.items():
            if k in name:
                return self.topic_cache[v]
        return self.topic_cache['andere']
