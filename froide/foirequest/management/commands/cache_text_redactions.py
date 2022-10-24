from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db.models.functions import Length
from django.utils import translation

from froide.helper.text_diff import get_differences


class Command(BaseCommand):
    help = "Pre-calculate cached redaction markup for long texts."

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)
        from froide.foirequest.models import FoiMessage
        from froide.foirequest.templatetags.foirequest_tags import (
            CONTENT_CACHE_THRESHOLD,
            render_message_content,
            unify,
        )

        needs_calculation = (
            Q(content_rendered_auth__isnull=True)
            | Q(content_rendered_anon__isnull=True)
            | Q(redacted_content_auth__isnull=True)
            | Q(redacted_content_anon__isnull=True)
        )

        msgs = (
            FoiMessage.objects.annotate(plaintext_length=Length("plaintext"))
            .filter(plaintext_length__gt=CONTENT_CACHE_THRESHOLD)
            .filter(needs_calculation)
        )

        for message in msgs:
            # render_message_content uses the 'unified' (aka NL instead of CRNL) content length to
            # calculate if the redacted content should be cached. The unification is done in python,
            # so we cannot filter this in the db and need to filter again here.
            if len(unify(message.plaintext)) <= CONTENT_CACHE_THRESHOLD:
                continue
            render_message_content(message, True)
            render_message_content(message, False)

            # Also cache the `redacted_content` property for the api
            message.redacted_content_auth = list(
                get_differences(message.plaintext_redacted, message.plaintext)
            )
            message.redacted_content_anon = list(
                get_differences(message.plaintext_redacted, message.plaintext)
            )
            message.save()
