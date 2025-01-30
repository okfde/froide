import json
import logging
from functools import partial

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from django.views.decorators.http import require_POST

from froide.foirequest.auth import can_read_foirequest
from froide.foirequest.utils import redact_plaintext_with_request
from froide.georegion.models import GeoRegion
from froide.helper.content_urls import get_content_url
from froide.helper.storage import make_unique_filename
from froide.helper.text_utils import slugify
from froide.helper.utils import is_ajax, is_fetch, render_400, render_403
from froide.proof.forms import handle_proof_form
from froide.upload.forms import get_uppy_i18n

from ..decorators import (
    allow_moderate_foirequest,
    allow_read_foirequest_authenticated,
    allow_write_foirequest,
    allow_write_or_moderate_foirequest,
    allow_write_or_moderate_pii_foirequest,
)
from ..forms import (
    EditMessageForm,
    PostalEditForm,
    PostalUploadForm,
    RedactMessageForm,
    TransferUploadForm,
    get_escalation_message_form,
    get_message_recipient_form,
    get_message_sender_form,
    get_postal_attachment_form,
    get_postal_message_form,
    get_postal_reply_form,
    get_send_message_form,
)
from ..models import FoiAttachment, FoiEvent, FoiMessage, FoiRequest
from ..models.attachment import IMAGE_FILETYPES, PDF_FILETYPES, POSTAL_CONTENT_TYPES
from ..models.message import MessageKind
from ..serializers import FoiAttachmentSerializer, FoiMessageSerializer
from ..services import ResendBouncedMessageService
from ..tasks import convert_images_to_pdf_task
from ..utils import check_throttle
from .request import show_foirequest

logger = logging.getLogger(__name__)


@require_POST
@allow_write_foirequest
def send_message(request, foirequest):
    form = get_send_message_form(request.POST, request.FILES, foirequest=foirequest)

    if foirequest.should_apply_throttle():
        # Only check throttle if last message is not a response
        throttle_message = check_throttle(foirequest.user, FoiMessage)
        if throttle_message:
            form.add_error(None, throttle_message)

    if form.is_valid():
        include_proof = handle_proof_form(request)
        mes = form.save(user=request.user, proof=include_proof)
        messages.add_message(
            request, messages.SUCCESS, _("Your message has been sent.")
        )
        return redirect(mes)

    return show_foirequest(
        request, foirequest, context={"send_message_form": form}, status=400
    )


@require_POST
@allow_write_foirequest
def escalation_message(request, foirequest):
    if not foirequest.can_be_escalated():
        messages.add_message(
            request, messages.ERROR, _("Your request cannot be escalated.")
        )
        return show_foirequest(request, foirequest, status=400)

    form = get_escalation_message_form(request.POST, foirequest=foirequest)

    if foirequest.should_apply_throttle():
        throttle_message = check_throttle(
            foirequest.user, FoiMessage, {"request": foirequest}
        )
        if throttle_message:
            form.add_error(None, throttle_message)

    if form.is_valid():
        message = form.save(user=request.user)
        messages.add_message(
            request, messages.SUCCESS, _("Your Escalation Message has been sent.")
        )
        return redirect(message)
    else:
        return show_foirequest(
            request, foirequest, context={"escalation_form": form}, status=400
        )


POSTAL_REPLY_SUCCESS = _("A postal reply was successfully added!")
POSTAL_REPLY_ERROR = _("There were errors with your form submission!")


@require_POST
@allow_write_foirequest
def add_postal_reply(
    request,
    foirequest,
    form_func=get_postal_reply_form,
    success_message=POSTAL_REPLY_SUCCESS,
    error_message=POSTAL_REPLY_ERROR,
    form_key="postal_reply_form",
):
    if not foirequest.public_body:
        return render_400(request)

    form = form_func(request.POST, request.FILES, foirequest=foirequest)

    if form.is_valid():
        message = form.save(request.user)

        messages.add_message(request, messages.SUCCESS, success_message)
        url = reverse(
            "foirequest-manage_attachments",
            kwargs={"slug": foirequest.slug, "message_id": message.id},
        )
        return redirect(url)

    messages.add_message(request, messages.ERROR, error_message)
    return show_foirequest(request, foirequest, context={form_key: form}, status=400)


def add_postal_message(request, slug):
    return add_postal_reply(
        request,
        slug,
        form_func=get_postal_message_form,
        success_message=_("A sent letter was successfully added!"),
        error_message=_("There were errors with your form submission!"),
        form_key="postal_message_form",
    )


@allow_write_foirequest
def upload_postal_message_create(request, foirequest):
    message, _created = FoiMessage.with_drafts.get_or_create(
        request=foirequest,
        kind=MessageKind.POST,
        is_draft=True,
        defaults={"timestamp": timezone.now()},
    )

    return redirect(
        reverse(
            "foirequest-edit_postal_message",
            kwargs={"slug": foirequest.slug, "message_id": message.id},
        )
    )


@allow_write_foirequest
def edit_postal_message(request, foirequest, message_id):
    message = get_object_or_404(
        FoiMessage.with_drafts, request=foirequest, pk=int(message_id)
    )
    if not message.can_edit:
        return render_400(request)
    form = PostalEditForm(
        data=request.POST,
        foirequest=foirequest,
        message=message,
        user=request.user,  # needs to be request user for upload ident
    )
    status_form = foirequest.get_status_form(data=request.POST)
    if request.method == "POST":
        if form.is_valid():
            message.is_draft = False
            message = form.save()

            if status_form.is_valid():
                status_form.save()

            if message.is_response:
                signal = FoiRequest.message_received
                success_message = _("A postal reply was successfully added!")
            else:
                signal = FoiRequest.message_sent
                success_message = _("A sent letter was successfully added!")

            signal.send(sender=foirequest, message=message, user=request.user)

            if is_fetch(request):
                return JsonResponse({"success": 1})

            messages.add_message(request, messages.SUCCESS, success_message)
            url = reverse(
                # after a successfully saved form, redirect to request
                "foirequest-show",
                kwargs={"slug": foirequest.slug},
            )
            return redirect(url)
        else:
            if is_fetch(request):
                return JsonResponse({"errors": form._errors})
            messages.add_message(
                request,
                messages.ERROR,
                _("There were errors with your form submission!"),
            )
    ctx = {
        "settings": {
            "tusChunkSize": settings.DATA_UPLOAD_MAX_MEMORY_SIZE - (500 * 1024),
            "can_make_document": request.user.is_staff,
            "allowed_filetypes": [".pdf", ".jpg", ".jpeg", ".png", ".gif"],
        },
        "user": {
            "can_edit_approval": request.user.is_staff,
        },
        "foirequest": {
            "public": foirequest.public,
        },
        "i18n": {
            "uppy": get_uppy_i18n(),
            # from publicbody/widgets
            "missingPublicBody": _("Are we missing a public body?"),
            "publicBodySearchPlaceholder": _("Ministry of..."),
            "search": _("Search"),
            "searchPublicBodyLabel": _("Search for public authorities"),
            "examples": _("Examples:"),
            "environment": _("Environment"),
            "ministryOfLabour": _("Ministry of Labour"),
            "or": _("or"),
            "noPublicBodiesFound": _("No Public Bodies found for this query."),
            "letUsKnow": _("Please let us know!"),
            # from views/attachment for <pdf-redaction>; not all might be necessary
            "previousPage": _("Previous Page"),
            "nextPage": _("Next Page"),
            "pageCurrentOfTotal": _("{current} of {total}").format(
                current="$current", total="$total"
            ),
            "redactAndPublish": _("Save redaction"),
            "publishWithoutRedaction": _("No redaction needed"),
            "removeAllRedaction": _("Remove all redaction"),
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
            # from upload_attachments
            "attachmentName": _("Name of attachment to create"),
            "newDocumentPageCount": [
                _("New document with one page"),
                _("New document with {count} pages").format(count="${count}"),
            ],
            "takePicture": _("Take / Choose picture"),
            "convertImages": _("Convert images to document"),
            "openAttachmentPage": _("Open attachment page"),
            "loadPreview": _("Preview"),
            "approveAll": _("Approve all"),
            "markAllAsResult": _("Mark all as result"),
            "otherAttachments": _("Other attachments that are not documents"),
            "imageDocumentExplanation": _(
                "Here you can combine your uploaded images to a PDF document. "
                "You can rearrange the pages and "
                "split it into multiple documents. "
                "You can redact the PDF in the next step."
            ),
            "documentPending": _(
                "This document is being generated. This can take several minutes."
            ),
            "documentDeleting": _("This document is being deleted..."),
            "documentTitle": _("Document title"),
            "documentTitleHelp": _("Give this document a proper title"),
            "documentTitlePlaceholder": _("e.g. Letter from date"),
            "showIrrelevantAttachments": _("Show irrelevant attachments"),
            "makeRelevant": _("Make relevant"),
            "loading": _("Loading..."),
            "description": _("Description"),
            "descriptionHelp": _("Describe the contents of the document"),
            "edit": _("Edit"),
            "save": _("Save"),
            "review": _("Review"),
            "approve": _("Approve"),
            "notPublic": _("not public"),
            "redacted": _("redacted"),
            "redact": _("Redact"),
            "moveTool": pgettext("redact tool", "Move"),
            "delete": _("Delete"),
            "confirmDelete": _("Are you sure you want to delete this attachment?"),
            "protectedOriginal": _("protected original"),
            "protectedOriginalExplanation": _(
                "This attachment has been converted to PDF and cannot be published."
            ),
            "isResult": _("Result?"),
            "makeResultExplanation": _(
                "Is this document a result of your request and not only correspondence?"
            ),
            "makeResultsExplanation": _(
                "Are these documents a result of your request and not only correspondence?"
            ),
            # for public body beta chooser, mostly from MakeRequestView
            "publicBodiesFound": [
                _("one public body found"),
                _("{count} public bodies found").format(count="${count}"),
            ],
            "administrativeUnitKind": _("Type of administrative unit"),
            "topicPlural": [
                _("Topic"),
                _("Topics"),
            ],
            "jurisdictionPlural": [
                _("Jurisdiction"),
                _("Jurisdictions"),
            ],
            "classificationPlural": [
                _("Classification"),
                _("Classifications"),
            ],
            "containingGeoregionsPlural": [
                _("Part of administrative region"),
                _("Part of administrative regions"),
            ],
            # from forms/message.py
            "scanHelpText": _("Uploaded scans can be PDF, JPG, PNG or GIF."),
            # post-upload.vue
            "step": _("Step"),
            "done": _("Done"),
            "back": _("Back"),
            "next": _("Next"),
            "new": _("New"),
            "documentsUploadDefaultFilename": _("letter.pdf"),
            "addLetter": _("Add letter"),
            "letterUploadOrScan": _("Upload or scan letter"),
            "enterInformation": _("Enter information"),
            "preview": _("Preview"),
            "scanDocuments": _("Scan documents"),
            "scanDocumentsAddendum": _("Use your phone's camera to create a PDF "),
            "uploadFiles": _("Upload files"),
            "uploadFilesAddendum": _("If you have the letter as PDF already"),
            "redactLaterHint1": _(
                "You don't need to redact your letter <strong>beforehand</strong>. You can do this later in the process using our browser tool."
            ),
            "redactLaterHint2": _(
                "We will guide you through the process step-by-step."
            ),
            "newLinkOldFlow": _(
                'Should you experience problems, you can use <a class="alert-link" href="${url}">the older version</a> here. We welcome feedback!'
            ),
            "newWarning": _("We have redone this part of the app."),
            "documentsDragOrder": _("Drag the documents in the right order"),
            "documentsFromImages": _("We will convert your images into a PDF"),
            "changeFilename": _("Change filename"),
            "documentsAvailable": _("Documents available so far"),
            "letterSentOrReceived": _(
                "Have you received or sent the uploaded document?"
            ),
            "messagePublicbodyCheckTo": _(
                "Is this the public body you have sent the letter to?"
            ),
            "messagePublicbodyCheckFrom": _(
                "Is this the public body that sent the letter?"
            ),
            "messagePublicbodyUpdateTo": _(
                "Which public body have you sent this letter to?"
            ),
            "messagePublicbodyUpdateFrom": _("Which public body has sent this letter?"),
            "messageDate": _("When was the letter sent?"),
            "messageIsRegisteredMail": _("The letter is registered mail"),
            "messageRegisteredMailInfo": _(
                "Registered mail is a postal service which allows the sender proof of mailing via a receipt. The letter can have a special envelope."
            ),
            "messageDateRegisteredMail": _(
                "Registered mail: what is the date stamped on the envelope?"
            ),
            "messageStatusIsResolvedAfterReceivedStill": _(
                "Your request was resolved. Is this still the case after you have received the letter?"
            ),
            "messageStatusIsResolvedAfterReceived": _(
                "Was your request resolved by this letter?"
            ),
            "messageStatusIsResolvedAfterSentStill": _(
                "Your request had already been resolved. Is this still the case after you have sent the letter?"
            ),
            "messageStatusIsResolvedAfterSent": _(
                "Was your request resolv by sending this letter?"
            ),
            "messageStatusIsResolvedStill": _("My request remains resolved."),
            "messageStatusIsResolvedNotAgain": _("My request is now unresolved."),
            "messageStatusIsResolved": _("Yes, the request is resolved."),
            "messageStatusIsResolvedNot": _("No, the request is not resolved yet."),
            "messageResolution": _("How would you characterize the result?"),
            "messageCost": _("How much compensation does the public body demand?"),
            "messageCostCheck": _("Did the public body demand compensation?"),
            "messageCostCheckLast": _(
                "You have noted that the public body had demanded compensation to the amount of €${amount}.<br/>Is this amount still correct?"
            ),
            "redactionPick": _("Which documents do you want to redact?"),
            "redactionInfo": _(
                "A document should be redacted when it contains information about yourself or the public body's employees."
            ),
            "selectAll": _("Select all"),
            "selectNone": _("Select none"),
            "redactionCounter": _("Redacting document ${current} of ${total}"),
            "helpNeeded": _("I have technical difficulties / I need help"),
            "documentsOverview": _("These documents will be added to the request:"),
            "documentsAddedSuccessfully": _("Documents added successfully"),
            "requestUpdatedThanks": _("Thank you for updating your request!"),
            "scanDocumentsAnother": _("Scan another document"),
            "uploadFilesAnother": _("Upload another file"),
            "redactionDone": _("I have finished redacting"),
            "redactionCheck": _("Important: Have you checked all pages?"),
            "confirm": _("Confirm"),
            "formHasErrors": _("The form has errors"),
            "requestNonPublicHint": _(
                "Your request is not public at the moment. The documents will not be public, either."
            ),
            "requestShow": _("See request"),
            "doneSorting": _("Done sorting"),
            "createPdf": _("Create PDF"),
            "documentsApproveLater": _("Uncheck to leave unpublished for now"),
        },
        "url": {
            "tusEndpoint": reverse("api:upload-list"),
            "legacyPostupload": reverse(
                "foirequest-upload_postal_message", kwargs={"slug": foirequest.slug}
            ),
            # from makerequest.py
            "searchPublicBody": reverse("api:publicbody-search"),
            "listJurisdictions": reverse("api:jurisdiction-list"),
            "listCategories": reverse("api:category-list"),
            "listClassifications": reverse("api:classification-list"),
            "listGeoregions": reverse("api:georegion-list"),
            "listPublicBodies": reverse("api:publicbody-list"),
            "listLaws": reverse("api:law-list"),
            "makeRequestTo": reverse(
                "foirequest-make_request", kwargs={"publicbody_ids": "0"}
            ),
            # from upload_attachments() TODO: might not need all
            "getMessage": reverse("api:message-detail", kwargs={"pk": message.id}),
            "getAttachment": reverse("api:attachment-detail", kwargs={"pk": 0}),
            "convertAttachments": reverse(
                "foirequest-manage_attachments",
                kwargs={"slug": foirequest.slug, "message_id": message.id},
            ),
            "addAttachment": reverse(
                "foirequest-add_postal_reply_attachment",
                kwargs={"slug": foirequest.slug, "message_id": message.id},
            ),
            "redactAttachment": reverse(
                "foirequest-redact_attachment",
                kwargs={"slug": foirequest.slug, "attachment_id": 0},
            ),
            "approveAttachment": reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": foirequest.slug, "attachment_id": 0},
            ),
            "deleteAttachment": reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": foirequest.slug, "attachment_id": 0},
            ),
            "createDocument": reverse(
                "foirequest-create_document",
                kwargs={"slug": foirequest.slug, "attachment_id": 0},
            ),
        },
        "urls": {
            # from views/attachment for <pdf-redaction>
            "publishUrl": reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": foirequest.slug, "attachment_id": 0},  # attachment.pk},
            ),
            "messageUpload": reverse(
                "foirequest-manage_attachments",
                kwargs={
                    "slug": foirequest.slug,
                    "message_id": 0,  # attachment.belongs_to_id,
                },
            ),
            "helpPostuploadRedaction": get_content_url("help_postupload_redaction"),
            # duplicated from url for compatibility with attachments.js TODO undup
            "getAttachment": reverse("api:attachment-detail", kwargs={"pk": 0}),
            "convertAttachments": reverse(
                "foirequest-manage_attachments",
                kwargs={"slug": foirequest.slug, "message_id": message.id},
            ),
            "mobileAppContent": settings.FROIDE_CONFIG.get("mobile_app_content_url")
            if request.user.is_staff
            else None,
            "messageWebsocket": "/ws/foimessage/{}/edit/".format(message.id),
        },
        "fixtures": {
            "georegion_kind": [
                [str(k), str(v)]
                for k, v in GeoRegion.KIND_CHOICES
                if k in settings.FROIDE_CONFIG.get("filter_georegion_kinds", [])
            ],
        },
    }
    return render(
        request,
        "foirequest/upload_postal_message_new.html",
        {
            "object": foirequest,
            "object_public_body_id": foirequest.public_body_id,
            "object_public_body": {
                "id": foirequest.public_body.id,
                "name": foirequest.public_body.name,
            },
            "object_public_body_json": json.dumps(
                {
                    "id": foirequest.public_body.id,
                    "name": foirequest.public_body.name,
                }
            ),
            "date_max": timezone.localdate().isoformat(),
            "date_min": foirequest.created_at.date().isoformat(),
            "object_public_json": json.dumps(foirequest.public),
            "user_is_staff": json.dumps(request.user.is_staff),
            "form": form,
            "message_json": "null"
            if message is None
            else json.dumps(
                FoiMessageSerializer(message, context={"request": request}).data
            ),
            "status_form": status_form,
            "config_json": json.dumps(ctx),
        },
    )


# TODO: remove in favor of API endpoint
@allow_write_foirequest
def upload_postal_message(request, foirequest):
    if request.method == "POST":
        form = PostalUploadForm(
            data=request.POST,
            foirequest=foirequest,
            user=request.user,  # needs to be request user for upload ident
        )
        status_form = foirequest.get_status_form(data=request.POST)
        if form.is_valid():
            message = form.save()

            if status_form.is_valid():
                status_form.save()

            if message.is_response:
                signal = FoiRequest.message_received
                success_message = _("A postal reply was successfully added!")
            else:
                signal = FoiRequest.message_sent
                success_message = _("A sent letter was successfully added!")

            signal.send(sender=foirequest, message=message, user=request.user)
            messages.add_message(request, messages.SUCCESS, success_message)

            url = reverse(
                "foirequest-manage_attachments",
                kwargs={"slug": foirequest.slug, "message_id": message.id},
            )
            return redirect(url)
        else:
            messages.add_message(
                request,
                messages.ERROR,
                _("There were errors with your form submission!"),
            )
    else:
        form = PostalUploadForm(foirequest=foirequest)
        status_form = foirequest.get_status_form()
    return render(
        request,
        "foirequest/upload_postal_message.html",
        {
            "object": foirequest,
            "form": form,
            "status_form": status_form,
        },
    )


def get_attachment_update_response(request, added_attachments):
    return JsonResponse(
        {
            "added": [
                FoiAttachmentSerializer(a, context={"request": request}).data
                for a in added_attachments
            ],
        }
    )


# TODO: remove in favor of API endpoint
@require_POST
@allow_write_foirequest
def add_postal_reply_attachment(request, foirequest, message_id):
    try:
        message = FoiMessage.with_drafts.get(request=foirequest, pk=int(message_id))
    except (ValueError, FoiMessage.DoesNotExist):
        raise Http404 from None
    if not message.is_postal:
        return render_400(request)

    form = get_postal_attachment_form(request.POST, request.FILES, foimessage=message)
    if form.is_valid():
        added = form.save(message)

        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.ATTACHMENT_UPLOADED,
            foirequest,
            message=message,
            user=request.user,
            **{"added": str(added)},
        )

        if is_ajax(request):
            return get_attachment_update_response(request, added)

        status_message = _("You added %d document(s) to this message.") % len(added)
        messages.add_message(request, messages.SUCCESS, status_message)
        return redirect(message)

    if is_ajax(request):
        return JsonResponse(
            {
                "error": form._errors["files"][0],
            }
        )

    messages.add_message(request, messages.ERROR, form._errors["files"][0])
    return render_400(request)


# TODO: remove in favor of API endpoint
def convert_to_pdf(request, foirequest, message, data):
    att_ids = [a["id"] for a in data["images"]]
    title = data.get("title") or _("letter")
    existing_names = {a.name for a in message.attachments}

    atts = message.foiattachment_set.filter(
        id__in=att_ids, filetype__startswith="image/"
    )
    safe_att_ids = {a.id for a in atts}
    att_ids = [aid for aid in att_ids if aid in safe_att_ids]

    name = "{}.pdf".format(slugify(title))
    name = make_unique_filename(name, existing_names)

    can_approve = not foirequest.not_publishable
    att = FoiAttachment.objects.create(
        name=name,
        belongs_to=message,
        approved=False,
        filetype="application/pdf",
        is_converted=True,
        can_approve=can_approve,
    )

    FoiAttachment.objects.filter(id__in=att_ids).update(
        converted_id=att.id, can_approve=False, approved=False
    )
    instructions = {d["id"]: d for d in data["images"] if d["id"] in att_ids}
    instructions = [instructions[i] for i in att_ids]

    transaction.on_commit(
        partial(
            convert_images_to_pdf_task.delay,
            att_ids,
            att.id,
            instructions,
            can_approve=can_approve,
        )
    )

    attachment_data = FoiAttachmentSerializer(att, context={"request": request}).data
    return JsonResponse(attachment_data)


# TODO: remove in favor of API endpoint
def add_tus_attachment(request, foirequest, message, data):
    form = TransferUploadForm(data=data, foimessage=message, user=request.user)
    if form.is_valid():
        added = form.save(request)
        return get_attachment_update_response(request, added)

    return JsonResponse({"error": True, "message": str(form.errors)})


# TODO: remove form in favor of API endpoint
@allow_write_foirequest
def upload_attachments(request, foirequest, message_id):
    try:
        message = FoiMessage.with_drafts.get(request=foirequest, pk=int(message_id))
    except (ValueError, FoiMessage.DoesNotExist):
        raise Http404 from None

    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except ValueError:
            raise Http404 from None
        actions = {
            "convert_to_pdf": convert_to_pdf,
            "add_tus_attachment": add_tus_attachment,
        }
        action = data.get("action")
        action_func = actions.get(action)
        if action_func is None:
            raise Http404
        try:
            return action_func(request, foirequest, message, data)
        except Exception as e:
            logger.exception(e)
            return JsonResponse({"error": True})

    attachment_form = get_postal_attachment_form(foimessage=message)

    ctx = {
        "user": {
            "can_edit_approval": request.user.is_staff,
        },
        "foirequest": {
            "public": foirequest.public,
        },
        "settings": {
            "can_make_document": request.user.is_staff,
            "document_filetypes": POSTAL_CONTENT_TYPES,
            "image_filetypes": IMAGE_FILETYPES,
            "pdf_filetypes": PDF_FILETYPES,
            "allowed_filetypes": ["application/pdf", "image/*"]
            + message.get_extra_content_types(),
            "attachment_form_prefix": attachment_form.prefix,
            "tusChunkSize": settings.DATA_UPLOAD_MAX_MEMORY_SIZE - (500 * 1024),
        },
        "url": {
            "getMessage": reverse("api:message-detail", kwargs={"pk": message.id}),
            "getAttachment": reverse("api:attachment-detail", kwargs={"pk": 0}),
            "convertAttachments": reverse(
                "foirequest-manage_attachments",
                kwargs={"slug": foirequest.slug, "message_id": message.id},
            ),
            "addAttachment": reverse(
                "foirequest-add_postal_reply_attachment",
                kwargs={"slug": foirequest.slug, "message_id": message.id},
            ),
            "redactAttachment": reverse(
                "foirequest-redact_attachment",
                kwargs={"slug": foirequest.slug, "attachment_id": 0},
            ),
            "approveAttachment": reverse(
                "foirequest-approve_attachment",
                kwargs={"slug": foirequest.slug, "attachment_id": 0},
            ),
            "deleteAttachment": reverse(
                "foirequest-delete_attachment",
                kwargs={"slug": foirequest.slug, "attachment_id": 0},
            ),
            "tusEndpoint": reverse("api:upload-list"),
            "createDocument": reverse(
                "foirequest-create_document",
                kwargs={"slug": foirequest.slug, "attachment_id": 0},
            ),
        },
        "i18n": {
            "attachmentName": _("Name of attachment to create"),
            "newDocumentPageCount": [
                _("New document with one page"),
                _("New document with {count} pages").format(count="${count}"),
            ],
            "takePicture": _("Take / Choose picture"),
            "convertImages": _("Convert images to document"),
            "openAttachmentPage": _("Open attachment page"),
            "loadPreview": _("Preview"),
            "approveAll": _("Approve all"),
            "markAllAsResult": _("Mark all as result"),
            "otherAttachments": _("Other attachments that are not documents"),
            "imageDocumentExplanation": _(
                "Here you can combine your uploaded images to a PDF document. "
                "You can rearrange the pages and "
                "split it into multiple documents. "
                "You can redact the PDF in the next step."
            ),
            "documentPending": _(
                "This document is being generated. This can take several minutes."
            ),
            "documentDeleting": _("This document is being deleted..."),
            "documentTitle": _("Document title"),
            "documentTitleHelp": _("Give this document a proper title"),
            "documentTitlePlaceholder": _("e.g. Letter from date"),
            "showIrrelevantAttachments": _("Show irrelevant attachments"),
            "makeRelevant": _("Make relevant"),
            "makePublic": pgettext("Attachment manager", "Make public"),
            "loading": _("Loading..."),
            "description": _("Description"),
            "descriptionHelp": _("Describe the contents of the document"),
            "edit": _("Edit"),
            "save": _("Save"),
            "review": _("Review"),
            "approve": _("Approve"),
            "notPublic": _("not public"),
            "redacted": _("redacted"),
            "nonRedacted": _("non-redacted"),
            "new": _("New"),
            "redact": _("Redact"),
            "delete": _("Delete"),
            "confirmDelete": _("Are you sure you want to delete this attachment?"),
            "protectedOriginal": _("protected original"),
            "protectedOriginalExplanation": _(
                "This attachment has been converted to PDF and cannot be published."
            ),
            "isResult": _("Result?"),
            "makeResultExplanation": _(
                "Is this document a result of your request and not only correspondence?"
            ),
            "makeResultsExplanation": _(
                "Are these documents a result of your request and not only correspondence?"
            ),
            "selectAll": _("Select all"),
            "selectNone": _("Select none"),
            "deleteSelected": _("Delete selected"),
            "downloadSelected": _("Download selected"),
            "markResult": _("Mark as result"),
            "markNotIrrelevant": _("Mark as important"),
            "editRedaction": _("Edit redaction"),
            "download": _("Download"),
            "downloadUnredacted": _("Download non-redacted"),
            "downloadOriginal": _("Download original"),
            "otherActions": _("Other actions"),
            "imageFile": _("Image file"),
            "size": _("Size"),
            "fileType": _("File type"),
            "actions": _("Actions"),
            "properties": _("Properties"),
            "uppy": get_uppy_i18n(),
        },
    }
    request.auth = None
    serializer = FoiMessageSerializer(message, context={"request": request})
    return render(
        request,
        "foirequest/attachment/manage.html",
        {
            "object": foirequest,
            "message_json": json.dumps(serializer.data),
            "message": message,
            "foirequest": foirequest,
            "config_json": json.dumps(ctx),
        },
    )


# TODO: remove in favor of API endpoint
@require_POST
@allow_write_or_moderate_foirequest
def set_message_sender(request, foirequest, message_id):
    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    if not message.is_response:
        return render_400(request)
    form = get_message_sender_form(request.POST, foimessage=message)
    if form.is_valid():
        form.save()
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.SENDER_CHANGED,
            foirequest,
            message=message,
            user=request.user,
            public_body=message.sender_public_body,
        )
        return redirect(message)
    messages.add_message(request, messages.ERROR, form._errors["sender"][0])
    return render_400(request)


# TODO: remove in favor of API endpoint
@require_POST
@allow_write_or_moderate_foirequest
def set_message_recipient(request, foirequest, message_id):
    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    if message.is_response:
        return render_400(request)
    form = get_message_recipient_form(request.POST, foimessage=message)
    if form.is_valid():
        form.save()
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.RECIPIENT_CHANGED,
            foirequest,
            message=message,
            user=request.user,
            public_body=message.recipient_public_body,
        )
        return redirect(message)
    messages.add_message(request, messages.ERROR, form._errors["recipient"][0])
    return render_400(request)


@require_POST
@allow_write_foirequest
def approve_message(request, foirequest, message_id):
    mes = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    mes.content_hidden = False
    mes.save()
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.MESSAGE_APPROVED,
        foirequest,
        message=mes,
        user=request.user,
    )
    messages.add_message(request, messages.SUCCESS, _("Content published."))
    return redirect(mes.get_absolute_url())


@require_POST
@allow_write_foirequest
def edit_message(request, foirequest, message_id):
    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    if not message.can_edit:
        return render_400(request)
    form = EditMessageForm(data=request.POST, message=message)
    if form.is_valid():
        form.save()
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.MESSAGE_EDITED,
            foirequest,
            message=message,
            user=request.user,
            **form.cleaned_data,
        )
        return redirect(message.get_absolute_url())
    else:
        messages.add_message(request, messages.ERROR, form.errors)
        return redirect(message.request.get_absolute_url())


@require_POST
@allow_write_or_moderate_pii_foirequest
def redact_message(request, foirequest, message_id):
    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    if message.is_response and request.POST.get("unredact_closing"):
        message.plaintext_redacted = redact_plaintext_with_request(
            message.plaintext,
            foirequest,
            redact_closing=False,
        )
        message.clear_render_cache()
        message.save()
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.MESSAGE_REDACTED,
            foirequest,
            message=message,
            user=request.user,
            **{"action": "unredact_closing"},
        )
        return redirect(message.get_absolute_url())
    form = RedactMessageForm(request.POST)
    if form.is_valid():
        form.save(message)
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.MESSAGE_REDACTED,
            foirequest,
            message=message,
            user=request.user,
            **form.cleaned_data,
        )
    return redirect(message.get_absolute_url())


@allow_read_foirequest_authenticated
def download_message_pdf(request, foirequest, message_id):
    from ..pdf_generator import FoiRequestMessagePDFGenerator

    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)

    pdf_generator = FoiRequestMessagePDFGenerator(message)
    response = HttpResponse(
        pdf_generator.get_pdf_bytes(), content_type="application/pdf"
    )
    name = "%s-%s" % (message.timestamp.date().isoformat(), message.pk)
    response["Content-Disposition"] = 'attachment; filename="%s.pdf"' % name
    return response


@allow_write_foirequest
def download_message_letter_pdf(request, foirequest, message_id):
    from ..pdf_generator import LetterPDFGenerator

    message = get_object_or_404(
        FoiMessage, request=foirequest, pk=message_id, is_response=False
    )

    pdf_generator = LetterPDFGenerator(message)
    response = HttpResponse(
        pdf_generator.get_pdf_bytes(), content_type="application/pdf"
    )
    name = "%s-%s" % (message.timestamp.date().isoformat(), message.pk)
    response["Content-Disposition"] = 'attachment; filename="%s.pdf"' % name
    return response


@allow_read_foirequest_authenticated
def download_message_package(request, foirequest, message_id):
    from ..foi_mail import package_message

    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    response = HttpResponse(package_message(message), content_type="application/zip")
    name = "%s-%s" % (
        foirequest.slug,
        message.pk,
    )
    response["Content-Disposition"] = 'attachment; filename="%s.zip"' % name
    return response


@allow_write_foirequest
def download_original_email(request, foirequest, message_id):
    message = get_object_or_404(
        FoiMessage, request=foirequest, pk=message_id, is_response=True
    )

    data = message.get_original_email_from_imap()
    if not data:
        messages.add_message(
            request, messages.WARNING, _("Could not download original.")
        )
        return redirect(foirequest)

    response = HttpResponse(data, content_type="application/octet-stream")
    name = "%s-%s" % (
        foirequest.slug,
        message.pk,
    )
    response["Content-Disposition"] = 'attachment; filename="%s.eml"' % name
    return response


@require_POST
@allow_moderate_foirequest
def resend_message(request, foirequest, message_id):
    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    if not message.can_resend_bounce:
        raise Http404

    service = ResendBouncedMessageService(message)
    sent_message = service.process()

    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.MESSAGE_RESENT,
        foirequest,
        message=sent_message,
        user=request.user,
    )

    if is_ajax(request):
        return HttpResponse(sent_message.get_absolute_url())

    messages.add_message(request, messages.SUCCESS, _("The message has been re-sent."))
    return redirect(sent_message)


def message_shortlink(request, obj_id):
    foimessage = get_object_or_404(FoiMessage, pk=obj_id)
    if not can_read_foirequest(foimessage.request, request):
        return render_403(request)
    url = foimessage.get_absolute_url()
    return redirect(url)
