from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation

from ...foi_mail import _process_mail


class Command(BaseCommand):
    help = "Deliver an .eml file into froide for testing purposes"

    def add_arguments(self, parser):
        parser.add_argument("mail_filename", type=str)

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)

        mail_filename = options["mail_filename"]

        with open(mail_filename, "rb") as f:
            _process_mail(f.read(), manual=True)
