import json
import logging

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext as _
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.template.defaultfilters import slugify

from froide.helper.utils import render_400
from froide.helper.storage import add_number_to_filename
from froide.helper.document import (
    POSTAL_CONTENT_TYPES, IMAGE_FILETYPES, PDF_FILETYPES
)

from ..models import FoiMessage, FoiAttachment
from ..api_views import FoiMessageSerializer, FoiAttachmentSerializer
from ..forms import (
    get_send_message_form, get_postal_reply_form, get_postal_message_form,
    get_escalation_message_form, get_postal_attachment_form,
    get_message_sender_form
)
from ..utils import check_throttle
from ..tasks import convert_images_to_pdf_task

from .request import show_foirequest
from .request_actions import allow_write_foirequest


logger = logging.getLogger(__name__)


@require_POST
@allow_write_foirequest
def send_message(request, foirequest):
    form = get_send_message_form(
        request.POST, request.FILES, foirequest=foirequest
    )

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

    throttle_message = check_throttle(foirequest.user, FoiMessage)
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


@require_POST
@allow_write_foirequest
def add_postal_reply(request, foirequest, form_func=get_postal_reply_form,
            success_message=_('A postal reply was successfully added!'),
            error_message=_('There were errors with your form submission!'),
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

    att = FoiAttachment.objects.create(
        name=name,
        belongs_to=message,
        approved=False,
        filetype='application/pdf',
        is_converted=True,
        can_approve=True,
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
    convert_images_to_pdf_task.delay(att_ids, att.id, instructions)

    attachment_data = FoiAttachmentSerializer(att, context={
        'request': request
    }).data
    return JsonResponse(attachment_data)


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
            'convert_to_pdf': convert_to_pdf
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
            'document_filetypes': POSTAL_CONTENT_TYPES,
            'image_filetypes': IMAGE_FILETYPES,
            'pdf_filetypes': PDF_FILETYPES,
            'attachment_form_prefix': attachment_form.prefix
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
        },
        'i18n': {
            'newDocumentPageCount': [
                _('New document with one page'),
                _('New document with {count} pages').format(count='${count}'),
            ],
            'takePicture': _('Take / Choose picture'),
            'convertImages': _('Convert images to document'),
            'openAttachmentPage': _('Open attachment page'),
            'loadPreview': _('Load preview'),
            'uploadPdfOrPicture': _('Upload PDF or picture'),
            'otherAttachments': _('Other attachments that are not documents'),
            'imageDocumentExplanation': _(
                'Here you can combine your uploaded images to a PDF document. '
                'You can rearrange the pages and '
                'split it into multiple documents. '
                'You can redact the PDF in the next step.'
            ),
            'documentPending': _(
                'This document is being generated. '
                'This can take several minutes.'
            ),
            'documentDeleting': _('This document is being deleted...'),
            'documentTitle': _('Document title'),
            'documentTitlePlaceholder': _('e.g. Letter from date'),
            'showIrrelevantAttachments': _('Show irrelevant attachments'),
            'makeRelevant': _('Make relevant'),
            'loading': _('Loading...'),
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
    try:
        message = FoiMessage.objects.get(request=foirequest,
                pk=int(message_id))
    except (ValueError, FoiMessage.DoesNotExist):
        raise Http404
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
def approve_message(request, foirequest, message):
    mes = get_object_or_404(FoiMessage, id=int(message))
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
