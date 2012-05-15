from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings

from foiidea.models import Article


class Command(BaseCommand):
    help = "Recalculate Article Order"

    def handle(self, **options):
        translation.activate(settings.LANGUAGE_CODE)
        Article.objects.recalculate_order()
