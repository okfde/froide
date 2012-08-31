# -*- encoding: utf-8 -*-
import json

from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings
from django.template.defaultfilters import slugify


class Command(BaseCommand):
    help = "Loads Brandenburg"
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
        juris = Jurisdiction.objects.get(slug='brandenburg')

        laws = FoiLaw.objects.filter(jurisdiction=juris)
        # importing Brandenburg
        pb_cache = {}
        with file(filepath) as f:
            pbs = json.loads(f.read().decode('utf-8'))
            for pb in pbs:
                topic = self.get_topic(pb)
                classifications = pb['name'].split()
                if classifications[0].startswith(('Brandenburgisch', 'Der', 'Die', 'Das', 'Deutsche',)):
                    classification = classifications[1]
                elif classifications[0].startswith(('Zentrale', 'Staatl',)):
                    classification = u" ".join(classifications[:2])
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
                contact = u"%s\n%s" % (pb.get('Telefon', ''), pb.get('Telefax', ''))
                if 'Internet' in pb:
                    contact += '\n%s' % pb['Internet']
                if 'url' in pb:
                    contact += '\n%s' % pb['url']
                public_body = PublicBody.objects.create(
                    name=pb['name'],
                    slug=slugify(pb['name']),
                    topic=topic,
                    description="",
                    url=pb.get('Internet', pb.get('url', None)),
                    classification=classification,
                    classification_slug=slugify(classification),
                    email=pb.get('E-Mail', None),
                    contact=u"%s\n%s" % (pb.get('Telefon', ''), pb.get('Telefax', '')),
                    address=pb.get('address'),
                    website_dump='',
                    request_note='',
                    _created_by=sw,
                    _updated_by=sw,
                    confirmed=True,
                    site=site,
                    jurisdiction=juris
                )
                pb_cache[pb['url']] = public_body
                public_body.laws.add(*laws)
                self.stdout.write((u"%s\n" % public_body).encode('utf-8'))
            for pb in pbs:
                if 'parent' in pb and pb['parent'] and pb['parent'] in pb_cache:
                    public_body = pb_cache[pb['url']]
                    public_body.parent = pb_cache[pb['parent']]
                    public_body.root = pb_cache[pb['parent']]
                    public_body.save()

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
