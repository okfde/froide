from io import StringIO
from contextlib import contextmanager

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from froide.helper.email_sending import send_mail

from ...validators import PublicBodyValidator
from ...models import PublicBody


class Command(BaseCommand):
    help = "Validates public bodies"

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str, nargs='?', default=None)

    @contextmanager
    def get_stream(self, filename):
        if filename is None:
            stream = StringIO()
        else:
            if filename == '-':
                stream = self.stdout
            else:
                stream = open(filename, 'w')
        yield stream
        if filename is not None and filename != '-':
            stream.close()

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)
        filename = options['filename']

        pbs = PublicBody.objects.all().iterator()
        validator = PublicBodyValidator(pbs)

        with self.get_stream(filename) as stream:
            validator.write_csv(stream)

            if filename is None and not validator.is_valid:
                for name, email in settings.MANAGERS:
                    send_mail(
                        _('Public body validation results'),
                        _('Please find attached the results of the public body validation'),
                        email,
                        attachments=[
                            ('validation_result.csv', stream.getvalue().encode('utf-8'), 'text/csv')
                        ]
                    )
