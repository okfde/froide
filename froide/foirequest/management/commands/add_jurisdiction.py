from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation


class Command(BaseCommand):
    help = "Add correct jurisdiction to requests, publicbodies etc."

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)
        from froide.foirequest.models import FoiRequest
        from froide.publicbody.models import FoiLaw, Jurisdiction, PublicBody

        juris = Jurisdiction.objects.all()[0]
        laws = FoiLaw.objects.filter(jurisdiction=juris)
        for law in laws:
            PublicBody.objects.filter(laws=law).update(jurisdiction=juris)
            FoiRequest.objects.filter(law=law).update(jurisdiction=juris)
