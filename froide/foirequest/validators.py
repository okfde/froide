from django.utils.encoding import force_text
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

import magic

from froide.helper.document import POSTAL_CONTENT_TYPES


def get_content_type(scan):
    scan.seek(0)
    content_type = magic.from_buffer(scan.read(1024), mime=True)
    content_type = force_text(content_type)
    scan.seek(0)
    return content_type


def validate_upload_document(scan):
    content_type = get_content_type(scan)

    # FIXME: move this out of the validator
    if content_type:
        scan.content_type = content_type

    if content_type not in POSTAL_CONTENT_TYPES:
        raise ValidationError(
            _('The scanned letter must be either PDF, JPG or PNG,'
                ' but was detected as %(content_type)s!'), params={
                    'content_type': content_type
                }
        )


def clean_reference(value):
    if not value:
        return ''
    try:
        kind, value = value.split(':', 1)
    except ValueError:
        return ''
    try:
        return '%s:%s' % (kind, value)
    except ValueError:
        return ''
