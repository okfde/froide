from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from froide.foirequest.models import FoiProject


class Command(BaseCommand):
    help = "Repair numbering, request counts and public bodies of projects."

    def handle(self, *args, **options):
        # Requests of recently created projects may still be being created.
        cutoff = timezone.now() - timedelta(hours=1)
        for project in FoiProject._base_manager.filter(created__lt=cutoff):
            project.update_from_requests()
