from collections import Counter
import os
import shutil
import re
import json

from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings

from froide.foirequest.models import FoiAttachment
from froide.foirequest.models.attachment import upload_to
from froide.helper.storage import HashedFilenameStorage

BROKEN_ISO_NAME = re.compile(r'^(.*)(\.[a-z]{,5})nameiso-8859-\w+$')


class Command(BaseCommand):
    help = "Moves files to content hash based directory structure"

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str)
        parser.add_argument('run_all', nargs='?', type=str)
        parser.add_argument('run_now', nargs='?', type=str)

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)

        if not hasattr(os, 'scandir'):
            raise NotImplemented('Requires Python 3.5+')

        self.storage = HashedFilenameStorage()

        self.directory = options['directory']
        self.run_all = options.get('run_all') == 'all'
        self.run_now = options.get('run_now') == 'run-now'
        self.missing_attachments = []

        if not self.run_now:
            print('DRY RUN MODE')
        else:
            print('Running for real now')

        for folder in os.scandir(self.directory):
            if folder.is_dir():
                self.handle_folder(folder)

        with open('missing_attachments.json', 'w') as f:
            json.dump(self.missing_attachments, f)

    def handle_folder(self, folder):
        for file_entry in os.scandir(folder.path):
            if file_entry.is_file():
                message_id = int(folder.name)
                all_attachments = FoiAttachment.objects.filter(
                    belongs_to_id=message_id
                )
                result = self.handle_file(file_entry, all_attachments)
                if self.run_now and not self.run_all and result:
                    raise Exception('Not running all')
                print('-' * 20)

    def handle_file(self, file_entry, all_attachments):
        orig_file_path = os.path.abspath(file_entry.path)
        print(orig_file_path)

        attachment = self.get_attachment(file_entry.name, all_attachments)
        if attachment is None:
            print('Missing attachments')
            self.missing_attachments.append(orig_file_path)
            return False

        print(attachment.name, attachment.file.name)
        file_path = self.fix_filepath(orig_file_path)
        fixed_attachment_name = os.path.basename(file_path)
        fixed_attachment_name = self.get_unique_name(
            fixed_attachment_name, all_attachments
        )
        attachment.name = fixed_attachment_name

        upload_path = upload_to(attachment, fixed_attachment_name)
        with open(orig_file_path, 'rb') as f:
            stored_path = self.storage._get_content_name(upload_path, f)

        print(fixed_attachment_name, stored_path)

        new_path = os.path.join(settings.MEDIA_ROOT, stored_path)

        print('Move from %s to %s' % (orig_file_path, new_path))
        new_base_path = os.path.dirname(new_path)

        if not os.path.exists(new_path):
            print('Creating dirs for', new_base_path)
            if self.run_now:
                mode_kwarg = {}
                if settings.FILE_UPLOAD_DIRECTORY_PERMISSIONS is not None:
                    mode_kwarg['mode'] = settings.FILE_UPLOAD_DIRECTORY_PERMISSIONS
                os.makedirs(
                    new_base_path,
                    exist_ok=True,
                    **mode_kwarg
                )
                shutil.move(orig_file_path, new_path)
        else:
            print('File already exists!', new_base_path)
        if self.run_now:
            attachment.file.name = stored_path
            attachment.save()
        return True

    def fix_filepath(self, filename):
        match = BROKEN_ISO_NAME.match(filename)
        if match is not None:
            return BROKEN_ISO_NAME.sub('\\1\\2', filename)
        return filename

    def get_attachment(self, name, attachments):
        for att in attachments:
            if att.file.name.endswith(name):
                return att

    def get_unique_name(self, name, attachments):
        name_counter = Counter([a.name for a in attachments])
        index = 0
        while name_counter[name] > 1:
            index += 1
            path, ext = os.path.splitext(name)
            name = '%s_%d%s' % (path, index, ext)
        return name
