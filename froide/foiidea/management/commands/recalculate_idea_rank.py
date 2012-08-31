from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings


class Command(BaseCommand):
    help = "Recalculate Article Order"

    def handle(self, **options):
        translation.activate(settings.LANGUAGE_CODE)
        from froide.foiidea.models import Article
        Article.objects.recalculate_order()
