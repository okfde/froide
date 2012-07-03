from django.core.management.base import BaseCommand, CommandError
from django.utils import translation
from django.conf import settings

from froide.foirequest.email import fetch_and_process


class Command(BaseCommand):
    help = "Fetches and processes mail from the configured IMAP account"

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)

        count = 0
        try:
            count = fetch_and_process()
        except Exception as e:
            raise CommandError('Fetch raised an error: %s' % e)
        self.stdout.write('Successfully fetched and processed %(count)d mails\n' %
                {"count": count})
