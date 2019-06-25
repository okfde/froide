from dateutil import relativedelta

from django.conf import settings as django_settings

# Retrieve root settings dict
TUS_SETTINGS = getattr(django_settings, 'TUS_SETTINGS', {})

TUS_UPLOAD_EXPIRES = TUS_SETTINGS.get('UPLOAD_EXPIRES', relativedelta.relativedelta(days=1))
TUS_MAX_FILE_SIZE = TUS_SETTINGS.get('MAX_FILE_SIZE', 4294967296)  # in bytes
TUS_FILENAME_METADATA_FIELD = TUS_SETTINGS.get('FILENAME_METADATA_FIELD', 'filename')
