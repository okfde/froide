import json
import logging

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext as _
from django.http import Http404, JsonResponse, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.template.defaultfilters import slugify

from froide.helper.utils import render_400
from froide.helper.storage import add_number_to_filename

from ..models import FoiMessage, FoiAttachment
from ..models.attachment import (
    POSTAL_CONTENT_TYPES, IMAGE_FILETYPES, PDF_FILETYPES
)
from ..api_views import FoiMessageSerializer, FoiAttachmentSerializer
from ..forms import (
    get_send_message_form, get_postal_reply_form, get_postal_message_form,
    get_escalation_message_form, get_postal_attachment_form,
    get_message_sender_form, TransferUploadForm, EditMessageForm,
    RedactMessageForm
)
from ..utils import check_throttle
from ..tasks import convert_images_to_pdf_task
from ..pdf_generator import LetterPDFGenerator

from .request import show_foirequest
from .request_actions import allow_write_foirequest


logger = logging.getLogger(__name__)


@require_POST
@allow_write_foirequest
def send_message(request, foirequest):
    form = get_send_message_form(
        request.POST, request.FILES, foirequest=foirequest
    )

    if foirequest.should_apply_throttle():
        # Only check throttle if last message is not a response
        throttle_message = check_throttle(foirequest.user, FoiMessage)
        if throttle_message:
            form.add_error(None, throttle_message)

    if form.is_valid():
        mes = form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your message has been sent.'))
        return redirect(mes)
    else:
        return show_foirequest(request, foirequest, context={
            "send_message_form": form
        }, status=400)


@require_POST
@allow_write_foirequest
def escalation_message(request, foirequest):
    if not foirequest.can_be_escalated():
        messages.add_message(request, messages.ERROR,
                _('Your request cannot be escalated.'))
        return show_foirequest(request, foirequest, status=400)

    form = get_escalation_message_form(request.POST, foirequest=foirequest)

    if foirequest.should_apply_throttle():
        throttle_message = check_throttle(foirequest.user, FoiMessage, {
            'request': foirequest
        })
        if throttle_message:
            form.add_error(None, throttle_message)

    if form.is_valid():
        message = form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your Escalation Message has been sent.'))
        return redirect(message)
    else:
        return show_foirequest(request, foirequest, context={
            "escalation_form": form
        }, status=400)


POSTAL_REPLY_SUCCESS = _('A postal reply was successfully added!')
POSTAL_REPLY_ERROR = _('There were errors with your form submission!')


@require_POST
@allow_write_foirequest
def add_postal_reply(request, foirequest, form_func=get_postal_reply_form,
            success_message=POSTAL_REPLY_SUCCESS,
            error_message=POSTAL_REPLY_ERROR,
            form_key='postal_reply_form'):

    if not foirequest.public_body:
        return render_400(request)

    form = form_func(request.POST, request.FILES, foirequest=foirequest)

    if form.is_valid():
        message = form.save()
        messages.add_message(request, messages.SUCCESS, success_message)
        url = reverse('foirequest-upload_attachments',
                kwargs={'slug': foirequest.slug, 'message_id': message.id})
        return redirect(url)

    messages.add_message(request, messages.ERROR, error_message)
    return show_foirequest(request, foirequest, context={
        form_key: form
    }, status=400)


def add_postal_message(request, slug):
    return add_postal_reply(
        request,
        slug,
        form_func=get_postal_message_form,
        success_message=_('A sent letter was successfully added!'),
        error_message=_('There were errors with your form submission!'),
        form_key='postal_message_form'
    )


def get_attachment_update_response(request, added, updated):
    return JsonResponse({
        'added': [
            FoiAttachmentSerializer(a, context={
                'request': request
            }).data for a in added
        ],
        'updated': [
            FoiAttachmentSerializer(u, context={
                'request': request
            }).data for u in updated
        ],
    })


@require_POST
@allow_write_foirequest
def add_postal_reply_attachment(request, foirequest, message_id):
    try:
        message = FoiMessage.objects.get(
            request=foirequest, pk=int(message_id)
        )
    except (ValueError, FoiMessage.DoesNotExist):
        raise Http404
    if not message.is_postal:
        return render_400(request)

    form = get_postal_attachment_form(
        request.POST, request.FILES, foimessage=message
    )
    if form.is_valid():
        result = form.save(message)
        added, updated = result

        if request.is_ajax():
            return get_attachment_update_response(request, added, updated)

        added_count = len(added)
        updated_count = len(updated)

        if updated_count > 0 and not added_count:
            status_message = _(
                'You updated %d document(s) on this message'
            ) % updated_count
        elif updated_count > 0 and added_count > 0:
            status_message = _(
                'You added %(added)d and updated %(updated)d '
                'document(s) on this message') % {
                    'updated': updated_count, 'added': added_count
                    }
        elif added_count > 0:
            status_message = _(
                'You added %d document(s) to this message.'
            ) % added_count
        messages.add_message(request, messages.SUCCESS, status_message)
        return redirect(message)

    if request.is_ajax():
        return JsonResponse({
            'error': form._errors['files'][0],
        })

    messages.add_message(request, messages.ERROR,
            form._errors['files'][0])
    return render_400(request)


def convert_to_pdf(request, foirequest, message, data):
    att_ids = [a['id'] for a in data['images']]
    title = data.get('title') or _('letter')
    names = set(a.name for a in message.attachments)

    atts = message.foiattachment_set.filter(
        id__in=att_ids, filetype__startswith='image/'
    )
    safe_att_ids = {a.id for a in atts}
    att_ids = [aid for aid in att_ids if aid in safe_att_ids]

    name = '{}.pdf'.format(slugify(title))

    i = 0
    while True:
        if name not in names:
            break
        i += 1
        name = add_number_to_filename(name, i)

    can_approve = not foirequest.not_publishable
    att = FoiAttachment.objects.create(
        name=name,
        belongs_to=message,
        approved=False,
        filetype='application/pdf',
        is_converted=True,
        can_approve=can_approve,
    )

    FoiAttachment.objects.filter(id__in=att_ids).update(
        converted_id=att.id, can_approve=False, approved=False
    )
    instructions = {
        d['id']: d for d in data['images'] if d['id'] in att_ids
    }
    instructions = [
        instructions[i] for i in att_ids
    ]
    convert_images_to_pdf_task.delay(
        att_ids, att.id, instructions, can_approve=can_approve
    )

    attachment_data = FoiAttachmentSerializer(att, context={
        'request': request
    }).data
    return JsonResponse(attachment_data)


def add_tus_attachment(request, foirequest, message, data):
    form = TransferUploadForm(
        data=data, user=request.user
    )
    if form.is_valid():
        result = form.save(message)
        added, updated = result
        return get_attachment_update_response(request, added, updated)

    return JsonResponse({'error': True, 'message': str(form.errors)})


def get_uppy_i18n():
    return {
        'addMore': _('Add more'),
        'addMoreFiles': _('Add more files'),
        'addingMoreFiles': _('Adding more files'),
        'allowAccessDescription': _('In order to take pictures of your documents, please allow camera access.'),
        'allowAccessTitle': _('Please allow access to your camera'),
        # 'authenticateWith': _('Connect to %{pluginName}'),
        # 'authenticateWithTitle': _('Please authenticate with %{pluginName} to select files'),
        'back': _('Back'),
        'browse': _('browse'),
        'cancel': _('Cancel'),
        'cancelUpload': _('Cancel upload'),
        'chooseFiles': _('Choose files'),
        'closeModal': _('Close Modal'),
        # 'companionAuthError': _('Authorization required'),
        # 'companionError': _('Connection with Companion failed'),
        'complete': _('Complete'),
        'connectedToInternet': _('Connected to the Internet'),
        'copyLink': _('Copy link'),
        'copyLinkToClipboardFallback': _('Copy the URL below'),
        'copyLinkToClipboardSuccess': _('Link copied to clipboard'),
        'dashboardTitle': _('File Uploader'),
        'dashboardWindowTitle': _('File Uploader Window (Press escape to close)'),
        'dataUploadedOfTotal': _('%{complete} of %{total}'),
        'done': _('Done'),
        'dropHereOr': _('Drop files here or %{browse}'),
        'dropHint': _('Drop your files here'),
        'dropPaste': _('Drop files here, paste or %{browse}'),
        'dropPasteImport': _('Drop files here, paste, %{browse} or import from'),
        'edit': _('Edit'),
        'editFile': _('Edit file'),
        'editing': _('Editing %{file}'),
        'emptyFolderAdded': _('No files were added from empty folder'),
        'exceedsSize': _('This file exceeds maximum allowed size of'),
        'failedToUpload': _('Failed to upload %{file}'),
        'fileSource': _('File source: %{name}'),
        'filesUploadedOfTotal': {
            '0': _('%{complete} of %{smart_count} file uploaded'),
            '1': _('%{complete} of %{smart_count} files uploaded'),
            '2': _('%{complete} of %{smart_count} files uploaded'),
        },
        'filter': _('Filter'),
        'finishEditingFile': _('Finish editing file'),
        'folderAdded': {
            '0': _('Added %{smart_count} file from %{folder}'),
            '1': _('Added %{smart_count} files from %{folder}'),
            '2': _('Added %{smart_count} files from %{folder}'),
        },
        'import': _('Import'),
        'importFrom': _('Import from %{name}'),
        'link': _('Link'),
        'loading': _('Loading...'),
        'myDevice': _('My Device'),
        'noFilesFound': _('You have no files or folders here'),
        'noInternetConnection': _('No Internet connection'),
        'pause': _('Pause'),
        'pauseUpload': _('Pause upload'),
        'paused': _('Paused'),
        'preparingUpload': _('Preparing upload...'),
        'processingXFiles': {
            '0': _('Processing %{smart_count} file'),
            '1': _('Processing %{smart_count} files'),
            '2': _('Processing %{smart_count} files'),
        },
        'removeFile': _('Remove file'),
        'resetFilter': _('Reset filter'),
        'resume': _('Resume'),
        'resumeUpload': _('Resume upload'),
        'retry': _('Retry'),
        'retryUpload': _('Retry upload'),
        'saveChanges': _('Save changes'),
        'selectXFiles': {
            '0': _('Select %{smart_count} file'),
            '1': _('Select %{smart_count} files'),
            '2': _('Select %{smart_count} files'),
        },
        'takePicture': _('Take a picture'),
        'timedOut': _('Upload stalled for %{seconds} seconds, aborting.'),
        'upload': _('Upload'),
        'uploadComplete': _('Upload complete'),
        'uploadFailed': _('Upload failed'),
        'uploadPaused': _('Upload paused'),
        'uploadXFiles': {
            '0': _('Upload %{smart_count} file'),
            '1': _('Upload %{smart_count} files'),
            '2': _('Upload %{smart_count} files'),
        },
        'uploadXNewFiles': {
            '0': _('Upload +%{smart_count} file'),
            '1': _('Upload +%{smart_count} files'),
            '2': _('Upload +%{smart_count} files'),
        },
        'uploading': _('Uploading'),
        'uploadingXFiles': {
            '0': _('Uploading %{smart_count} file'),
            '1': _('Uploading %{smart_count} files'),
            '2': _('Uploading %{smart_count} files'),
        },
        'xFilesSelected': {
            '0': _('%{smart_count} file selected'),
            '1': _('%{smart_count} files selected'),
            '2': _('%{smart_count} files selected'),
        },
        'xMoreFilesAdded': {
            '0': _('%{smart_count} more file added'),
            '1': _('%{smart_count} more files added'),
            '2': _('%{smart_count} more files added'),
        },
        'xTimeLeft': _('%{time} left'),
        'youCanOnlyUploadFileTypes': _('You can only upload: %{types}'),
    }


@allow_write_foirequest
def upload_attachments(request, foirequest, message_id):
    try:
        message = FoiMessage.objects.get(
            request=foirequest, pk=int(message_id)
        )
    except (ValueError, FoiMessage.DoesNotExist):
        raise Http404

    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise Http404
        actions = {
            'convert_to_pdf': convert_to_pdf,
            'add_tus_attachment': add_tus_attachment,
        }
        action = data.get('action')
        action_func = actions.get(action)
        if action_func is None:
            raise Http404
        try:
            return action_func(request, foirequest, message, data)
        except Exception as e:
            logger.exception(e)
            return JsonResponse({'error': True})

    attachment_form = get_postal_attachment_form(foimessage=message)

    ctx = {
        'settings': {
            'can_make_document': request.user.is_staff,
            'document_filetypes': POSTAL_CONTENT_TYPES,
            'image_filetypes': IMAGE_FILETYPES,
            'pdf_filetypes': PDF_FILETYPES,
            'attachment_form_prefix': attachment_form.prefix,
            'tusChunkSize': settings.DATA_UPLOAD_MAX_MEMORY_SIZE - (500 * 1024)
        },
        'resources': {
            'pdfjsWorker': static('js/pdf.worker.min.js')
        },
        'url': {
            'getMessage': reverse('api:message-detail', kwargs={
                'pk': message.id
            }),
            'getAttachment': reverse('api:attachment-detail', kwargs={
                'pk': 0
            }),
            'convertAttachments': reverse('foirequest-upload_attachments',
                kwargs={'slug': foirequest.slug, 'message_id': message.id}),
            'addAttachment': reverse('foirequest-add_postal_reply_attachment',
                kwargs={'slug': foirequest.slug, 'message_id': message.id}),
            'redactAttachment': reverse('foirequest-redact_attachment',
                kwargs={'slug': foirequest.slug, 'attachment_id': 0}),
            'approveAttachment': reverse('foirequest-approve_attachment',
                kwargs={'slug': foirequest.slug, 'attachment': 0}),
            'deleteAttachment': reverse('foirequest-delete_attachment',
                kwargs={'slug': foirequest.slug, 'attachment': 0}),
            'tusEndpoint': reverse('api:upload-list'),
            'createDocument': reverse('foirequest-create_document',
                kwargs={'slug': foirequest.slug, 'attachment': 0}),
        },
        'i18n': {
            'newDocumentPageCount': [
                _('New document with one page'),
                _('New document with {count} pages').format(count='${count}'),
            ],
            'takePicture': _('Take / Choose picture'),
            'convertImages': _('Convert images to document'),
            'openAttachmentPage': _('Open attachment page'),
            'loadPreview': _('Preview'),
            'uploadPdfOrPicture': _('Upload PDFs or pictures of documents.'),
            'upload': _('Upload'),
            'otherAttachments': _('Other attachments that are not documents'),
            'convertImagesToDocuments': _('Convert images to documents'),
            'imageDocumentExplanation': _(
                'Here you can combine your uploaded images to a PDF document. '
                'You can rearrange the pages and '
                'split it into multiple documents. '
                'You can redact the PDF in the next step.'
            ),
            'documents': _('Documents'),
            'otherFiles': _('Other files'),
            'documentPending': _(
                'This document is being generated. '
                'This can take several minutes.'
            ),
            'documentDeleting': _('This document is being deleted...'),
            'documentTitle': _('Document title'),
            'documentTitleHelp': _('Give this document a proper title'),
            'documentTitlePlaceholder': _('e.g. Letter from date'),
            'showIrrelevantAttachments': _('Show irrelevant attachments'),
            'makeRelevant': _('Make relevant'),
            'loading': _('Loading...'),
            'description': _('Description'),
            'descriptionHelp': _('Describe the contents of the document'),
            'edit': _('Edit'),
            'save': _('Save'),
            'review': _('Review'),
            'approve': _('Approve'),
            'notPublic': _('not public'),
            'redacted': _('redacted'),
            'redact': _('Redact'),
            'delete': _('Delete'),
            'confirmDelete': _(
                'Are you sure you want to delete this attachment?'
            ),
            'protectedOriginal': _('protected original'),
            'protectedOriginalExplanation': _(
                'This attachment has been converted to PDF and '
                'cannot be published.'
            ),
            'isResult': _('Result?'),
            'makeResultExplanation': _('Is this document a result of your request and not only correspondence?'),
            'makeResultsExplanation': _('Are these documents a result of your request and not only correspondence?'),
            'uppy': get_uppy_i18n()
        }
    }
    request.auth = None
    serializer = FoiMessageSerializer(message, context={
        'request': request
    })
    return render(request, 'foirequest/attachment/upload.html', {
        'message_json': json.dumps(serializer.data),
        'message': message,
        'foirequest': foirequest,
        'config_json': json.dumps(ctx)
    })


@require_POST
@allow_write_foirequest
def set_message_sender(request, foirequest, message_id):
    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    if not message.is_response:
        return render_400(request)
    form = get_message_sender_form(request.POST, foimessage=message)
    if form.is_valid():
        form.save()
        return redirect(message)
    messages.add_message(request, messages.ERROR,
            form._errors['sender'][0])
    return render_400(request)


@require_POST
@allow_write_foirequest
def approve_message(request, foirequest, message_id):
    mes = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    mes.content_hidden = False
    mes.save()
    messages.add_message(request, messages.SUCCESS,
            _('Content published.'))
    return redirect(mes.get_absolute_url())


@require_POST
@allow_write_foirequest
def resend_message(request, foirequest):
    try:
        mes = FoiMessage.objects.get(
            sent=False,
            request=foirequest,
            pk=int(request.POST.get('message', 0))
        )
    except (FoiMessage.DoesNotExist, ValueError):
        messages.add_message(request, messages.ERROR,
                    _('Invalid input!'))
        return render_400(request)
    mes.resend()
    return redirect('admin:foirequest_foimessage_change', mes.id)


@require_POST
@allow_write_foirequest
def edit_message(request, foirequest, message_id):
    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    if not message.can_edit:
        return render_400(request)
    form = EditMessageForm(data=request.POST, message=message)
    if form.is_valid():
        form.save()
    return redirect(message.get_absolute_url())


@require_POST
@allow_write_foirequest
def redact_message(request, foirequest, message_id):
    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    form = RedactMessageForm(request.POST)
    if form.is_valid():
        form.save(message)
    return redirect(message.get_absolute_url())


@allow_write_foirequest
def download_message_pdf(request, foirequest, message_id):
    message = get_object_or_404(
        FoiMessage,
        request=foirequest, pk=message_id,
        is_response=False
    )

    pdf_generator = LetterPDFGenerator(message)
    response = HttpResponse(
        pdf_generator.get_pdf_bytes(),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = 'attachment; filename="%s.pdf"' % foirequest.pk
    return response
