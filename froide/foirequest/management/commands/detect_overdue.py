from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings

from froide.foirequest.models import FoiRequest


class Command(BaseCommand):
    help = "Sets all overdue requests to overdue"

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)
        for foirequest in FoiRequest.objects.get_overdue():
            foirequest.set_overdue()
