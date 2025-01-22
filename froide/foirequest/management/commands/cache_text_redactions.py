from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q, QuerySet
from django.db.models.functions import Length
from django.utils import translation

from froide.foirequest.models.request import FoiRequest
from froide.helper.text_diff import CONTENT_CACHE_THRESHOLD


class Command(BaseCommand):
    help = "Pre-calculate redaction diffs and markup for long texts."

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)
        from froide.foirequest.models import FoiMessage
        from froide.foirequest.templatetags.foirequest_tags import (
            render_message_content,
            render_request_description,
        )

        needs_calculation = (
            Q(content_rendered_auth__isnull=True)
            | Q(content_rendered_anon__isnull=True)
            | Q(redacted_content_auth__isnull=True)
            | Q(redacted_content_anon__isnull=True)
        )

        msgs: QuerySet[FoiMessage] = (
            FoiMessage.objects.annotate(plaintext_length=Length("plaintext"))
            .filter(plaintext_length__gt=CONTENT_CACHE_THRESHOLD)
            .filter(needs_calculation)
        )

        for message in msgs:
            # Cache the `redacted_content` property for the api
            message.get_redacted_content(True)
            message.get_redacted_content(False)

            # Cache the rendered message content for the foi request page
            render_message_content(message, True)
            render_message_content(message, False)

        reqs: QuerySet[FoiRequest] = (
            FoiRequest.objects.annotate(description_length=Length("description"))
            .filter(description_length__gt=CONTENT_CACHE_THRESHOLD)
            .filter(
                Q(redacted_description_auth__isnull=True)
                | Q(redacted_description_anon__isnull=True)
                | Q(rendered_description_auth__isnull=True)
                | Q(rendered_description_anon__isnull=True)
            )
        )
        for req in reqs:
            req.get_redacted_description(True)
            req.get_redacted_description(False)
            render_request_description(req, True)
            render_request_description(req, False)
