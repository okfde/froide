# -*- encoding: utf-8 -*-
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation


class Command(BaseCommand):
    help = "Loads public bodies"

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str)

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)

        from froide.publicbody.csv_import import CSVImporter

        filename = options['filename']

        importer = CSVImporter()

        if filename.startswith('http://') or filename.startswith('https://'):
            importer.import_from_url(filename)
        else:
            importer.import_from_file(open(filename, 'rb'))

        self.stdout.write(u"Import done.\n")
