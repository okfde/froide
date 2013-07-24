# -*- encoding: utf-8 -*-
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation


class Command(BaseCommand):
    help = "Loads public bodies"

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)

        from froide.publicbody.csv_import import CSVImporter

        importer = CSVImporter()

        if len(args) != 1:
            self.stderr.write((u"Give URL or filename!\n").encode('utf-8'))
            return 1

        if args[0].startswith('http://') or args[0].startswith('https://'):
            importer.import_from_url(args[0])
        else:
            importer.import_from_file(file(args[0]))

        self.stdout.write((u"Import done.\n").encode('utf-8'))
