from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation

from froide.helper.email_log_parsing import check_delivery_from_log


class Command(BaseCommand):
    help = "Processes mail logs for deliveries"

    def add_arguments(self, parser):
        parser.add_argument("log_path", default=None)

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)
        check_delivery_from_log(options["log_path"])
