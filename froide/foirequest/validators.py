from django.core.exceptions import ValidationError
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from .models.attachment import POSTAL_CONTENT_TYPES


def get_content_type(scan):
    import magic

    scan.seek(0)
    content_type = magic.from_buffer(scan.read(1024), mime=True)
    content_type = force_str(content_type)
    scan.seek(0)
    return content_type


def validate_upload_document(scan):
    content_type = get_content_type(scan)

    # FIXME: move this out of the validator
    if content_type:
        scan.content_type = content_type

    validate_postal_content_type(content_type)


def validate_postal_content_type(content_type):
    if content_type not in POSTAL_CONTENT_TYPES:
        raise ValidationError(
            _(
                "The scanned letter must be either PDF, JPG or PNG,"
                " but was detected as %(content_type)s!"
            ),
            params={"content_type": content_type},
        )


def clean_reference(value):
    if not value:
        return ""
    try:
        kind, value = value.split(":", 1)
    except ValueError:
        return ""
    try:
        return "%s:%s" % (kind, value)
    except ValueError:
        return ""


PLACEHOLDER_MARKER = "…"  # Single character, horizontal ellipsis U+2026


def validate_no_placeholder(value):
    if PLACEHOLDER_MARKER in value:
        raise ValidationError(
            _("Please replace all placeholder values marked by “{}”.").format(
                PLACEHOLDER_MARKER
            )
        )
