from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings


class Command(BaseCommand):
    help = "Update feed with id"

    def handle(self, source_id, **options):
        translation.activate(settings.LANGUAGE_CODE)
        from froide.foiidea.crawler import crawl_source_by_id
        crawl_source_by_id(int(source_id))
