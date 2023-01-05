import json
import logging
import re
from functools import partial

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import Http404, get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView

from crossdomainmedia import CrossDomainMediaMixin

from froide.helper.utils import is_ajax, render_400, render_403

from ..auth import (
    AttachmentCrossDomainMediaAuth,
    get_accessible_attachment_url,
    has_attachment_access,
)
from ..decorators import (
    allow_moderate_pii_foirequest,
    allow_write_foirequest,
    allow_write_or_moderate_pii_foirequest,
)
from ..models import FoiAttachment, FoiMessage, FoiRequest
from ..tasks import redact_attachment_task

logger = logging.getLogger(__name__)


def show_attachment(request, slug, message_id, attachment_name):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    message = get_object_or_404(FoiMessage, id=int(message_id), request=foirequest)
    try:
        attachment = FoiAttachment.objects.get_for_message(message, attachment_name)
    except FoiAttachment.DoesNotExist:
        raise Http404

    if not has_attachment_access(request, foirequest, attachment):
        if attachment.redacted and has_attachment_access(
            request, foirequest, attachment.redacted
        ):
            return redirect(attachment.redacted)
        return render_403(request)

    if attachment.document is not None and attachment.document.public:
        return redirect(attachment.document)

    attachment_url = get_accessible_attachment_url(foirequest, attachment)

    return render(
        request,
        "foirequest/attachment/show.html",
        {
            "attachment": attachment,
            "attachment_url": attachment_url,
            "message": message,
            "foirequest": foirequest,
        },
    )


@require_POST
@allow_write_or_moderate_pii_foirequest
def approve_attachment(request, foirequest, attachment_id):
    att = get_object_or_404(
        FoiAttachment, id=attachment_id, belongs_to__request=foirequest
    )
    if not att.can_approve and not request.user.is_staff:
        return render_403(request)

    # hard guard against publishing of non publishable requests
    if not foirequest.not_publishable:
        att.approve_and_save()
        att.attachment_approved.send(
            sender=att,
            user=request.user,
        )

    if is_ajax(request):
        if request.content_type == "application/json":
            return JsonResponse({})
        return HttpResponse(
            '<div class="alert alert-success">{}</div>'.format(
                _("Attachment approved.")
            )
        )
    messages.add_message(request, messages.SUCCESS, _("Attachment approved."))
    return redirect(att.get_anchor_url())


@require_POST
@allow_moderate_pii_foirequest
def mark_attachment_as_moderated(request, foirequest, attachment_id):
    att = get_object_or_404(
        FoiAttachment, id=attachment_id, belongs_to__request=foirequest
    )

    if not att.is_moderated:
        att.is_moderated = True
        att.save(update_fields=["is_moderated"])

    if is_ajax(request):
        if request.content_type == "application/json":
            return JsonResponse({})
        return HttpResponse(
            '<div class="alert alert-success">{}</div>'.format(
                _("Attachment has been marked as moderated.")
            )
        )
    messages.add_message(
        request, messages.SUCCESS, _("Attachment has been marked as moderated.")
    )
    return redirect(att.get_anchor_url())


@require_POST
@allow_write_foirequest
def delete_attachment(request, foirequest, attachment_id):
    att = get_object_or_404(
        FoiAttachment, id=attachment_id, belongs_to__request=foirequest
    )
    message = att.belongs_to
    if not message.is_postal:
        return render_403(request)
    if not att.can_delete:
        return render_403(request)
    if att.is_redacted:
        FoiAttachment.objects.filter(redacted=att).update(can_approve=True)
    att.attachment_deleted.send(
        sender=att,
        user=request.user,
    )
    att.remove_file_and_delete()

    if is_ajax(request):
        if request.content_type == "application/json":
            return JsonResponse({})
        return HttpResponse()
    messages.add_message(request, messages.SUCCESS, _("Attachment deleted."))
    return redirect(message.get_absolute_url())


@require_POST
@allow_write_or_moderate_pii_foirequest
def create_document(request, foirequest, attachment_id):
    att = get_object_or_404(
        FoiAttachment, id=attachment_id, belongs_to__request=foirequest
    )
    if not att.can_approve and not request.user.is_staff:
        return render_403(request)

    if att.redacted or att.converted or att.document is not None or not att.is_pdf:
        return render_400(request)

    doc = att.create_document()
    att.document_created.send(
        sender=att,
        user=request.user,
    )

    if is_ajax(request):
        return JsonResponse(
            {
                "resource_uri": reverse("api:document-detail", kwargs={"pk": doc.id}),
            }
        )
    messages.add_message(request, messages.SUCCESS, _("Document created."))

    return redirect(att.get_anchor_url())


class AttachmentFileDetailView(CrossDomainMediaMixin, DetailView):
    """
    Add the CrossDomainMediaMixin
    and set your custom media_auth_class
    """

    media_auth_class = AttachmentCrossDomainMediaAuth

    def get_object(self):
        self.message = get_object_or_404(FoiMessage, id=int(self.kwargs["message_id"]))
        try:
            return FoiAttachment.objects.get_for_message(
                self.message, self.kwargs["attachment_name"]
            )
        except FoiAttachment.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["foirequest"] = self.message.request
        return ctx

    def unauthorized(self, mauth):
        return render_403(self.request)

    def redirect_to_media(self, mauth):
        """
        Force direct links on main domain that are not
        refreshing a token to go to the objects page
        """
        # Check file authorization first
        url = mauth.get_authorized_media_url(self.request)

        # Check if download is requested
        download = self.request.GET.get("download")
        if download is None:
            # otherwise redirect to attachment page
            return redirect(self.object.get_absolute_url(), permanent=True)

        return redirect(url)

    def send_media_file(self, mauth):
        response = super().send_media_file(mauth)
        response["Link"] = '<{}>; rel="canonical"'.format(
            self.object.get_absolute_domain_url()
        )
        return response


def get_redact_context(foirequest, attachment):
    return {
        "urls": {
            "publishUrl": reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": foirequest.slug, "attachment_id": attachment.pk},
            ),
            "messageUpload": reverse(
                "foirequest-manage_attachments",
                kwargs={
                    "slug": foirequest.slug,
                    "message_id": attachment.belongs_to_id,
                },
            ),
        },
        "i18n": {
            "previousPage": _("Previous Page"),
            "nextPage": _("Next Page"),
            "pageCurrentOfTotal": _("{current} of {total}").format(
                current="$current", total="$total"
            ),
            "redactAndPublish": _("Save redaction"),
            "publishWithoutRedaction": _("No redaction needed"),
            "toggleText": _("Text only"),
            "disableText": _("Hide text"),
            "cancel": _("Cancel"),
            "undo": _("Undo"),
            "redo": _("Redo"),
            "loadingPdf": _("Loading PDF..."),
            "sending": _("Uploading redaction instructions, please wait..."),
            "redacting": _("Redacting PDF, please wait..."),
            "redactionError": _(
                "There was a problem with your redaction. Please contact moderators."
            ),
            "redactionTimeout": _(
                "Your redaction took too long. It may become available soon, if not, contact moderators."
            ),
            "autoRedacted": _(
                "We automatically redacted some text for you already. Please check if we got everything."
            ),
            "passwordRequired": _(
                "This PDF requires a password to open. Please provide the password here:"
            ),
            "passwordCancel": _(
                "The password you provided was incorrect. Do you want to abort?"
            ),
            "passwordMissing": _(
                "The PDF could not be opened because of a missing password. Please ask the authority to provide you with a password."
            ),
            "removePasswordAndPublish": _("Remove password and publish"),
            "hasPassword": _(
                "The original document is protected with a password. The password is getting removed on publication."
            ),
            "confirmNoRedactionTitle": _("Are you sure that no redaction is needed?"),
            "confirmNoRedactionsText": _(
                "You redacted parts of the document, but clicked that no redaction is needed. Are you sure that no redaction is needed?"
            ),
            "close": _("Close"),
        },
    }


@allow_write_or_moderate_pii_foirequest
def redact_attachment(request, foirequest, attachment_id):
    attachment = get_object_or_404(
        FoiAttachment, id=int(attachment_id), belongs_to__request=foirequest
    )
    if not attachment.can_redact:
        return render_403(request)

    already = None
    if attachment.redacted:
        already = attachment.redacted
    elif attachment.is_redacted:
        already = attachment

    if request.method == "POST":
        # Python 2.7/3.5 requires str for json.loads
        instructions = json.loads(request.body.decode("utf-8"))

        if already:
            att = already
            att.approved = False
            att.can_approve = False
            att.pending = True
            att.save()
        else:
            name = attachment.name.rsplit(".", 1)[0]
            name = re.sub(r"[^\w\.\-]", "", name)

            doc = None
            if attachment.document:
                # Attachment is original to be redacted
                # Move document
                doc = attachment.document
                attachment.document = None
                attachment.save()

            att = FoiAttachment.objects.create(
                belongs_to=attachment.belongs_to,
                name=_("%s_redacted.pdf") % name,
                is_redacted=True,
                filetype="application/pdf",
                approved=False,
                can_approve=False,
                document=doc,
            )
            if doc:
                doc.original = att
                doc.save()

        if not attachment.is_redacted:
            attachment.redacted = att
            attachment.can_approve = False
            attachment.approved = False
            attachment.save()

        transaction.on_commit(
            partial(redact_attachment_task.delay, attachment.id, att.id, instructions)
        )

        att.attachment_redacted.send(
            sender=att,
            user=request.user,
        )

        return JsonResponse(
            {
                "url": att.get_anchor_url(),
                "resource_uri": reverse("api:attachment-detail", kwargs={"pk": att.id}),
            }
        )

    attachment_url = get_accessible_attachment_url(foirequest, attachment)

    ctx = {
        "foirequest": foirequest,
        "attachment": attachment,
        "attachment_url": attachment_url,
        "config": json.dumps(get_redact_context(foirequest, attachment)),
    }

    return render(request, "foirequest/redact.html", ctx)
