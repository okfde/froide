from __future__ import unicode_literals

import re
import json

from django.conf import settings
from django.core.files import File
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse, JsonResponse
from django.contrib import messages

from froide.helper.utils import render_400, render_403
from froide.helper.redaction import redact_file

from ..models import FoiRequest, FoiMessage, FoiAttachment
from ..auth import (can_read_foirequest, can_read_foirequest_authenticated,
                    can_write_foirequest)


X_ACCEL_REDIRECT_PREFIX = getattr(settings, 'X_ACCEL_REDIRECT_PREFIX', '')


@require_POST
def approve_attachment(request, slug, attachment):
    foirequest = get_object_or_404(FoiRequest, slug=slug)

    if not can_write_foirequest(foirequest, request):
        return render_403(request)
    att = get_object_or_404(FoiAttachment, id=int(attachment))
    if not att.can_approve and not request.user.is_staff:
        return render_403(request)
    att.approve_and_save()
    messages.add_message(request, messages.SUCCESS,
            _('Attachment approved.'))
    return redirect(att.get_anchor_url())


def auth_message_attachment(request, message_id, attachment_name):
    '''
    nginx auth view
    '''
    message = get_object_or_404(FoiMessage, id=int(message_id))
    attachment = get_object_or_404(FoiAttachment, belongs_to=message,
        name=attachment_name)
    foirequest = message.request
    if not can_read_foirequest(foirequest, request):
        return render_403(request)
    if not attachment.approved:
        # allow only approved attachments to be read
        # do not allow anonymous authentication here
        allowed = can_read_foirequest_authenticated(
            foirequest, request, allow_code=False
        )
        if not allowed:
            return render_403(request)

    response = HttpResponse()
    response['Content-Type'] = ""
    response['X-Accel-Redirect'] = X_ACCEL_REDIRECT_PREFIX + attachment.get_internal_url()

    return response


def redact_attachment(request, slug, attachment_id):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not can_write_foirequest(foirequest, request):
        return render_403(request)
    attachment = get_object_or_404(FoiAttachment, pk=int(attachment_id),
            belongs_to__request=foirequest)
    if not attachment.can_approve and not request.user.is_staff:
        return render_403(request)
    already = None
    if attachment.redacted:
        already = attachment.redacted
    elif attachment.is_redacted:
        already = attachment

    if (already is not None and not already.can_approve and
            not request.user.is_staff):
        return render_403(request)

    if request.method == 'POST':
        # Python 2.7/3.5 requires str for json.loads
        instructions = json.loads(request.body.decode('utf-8'))
        path = redact_file(attachment.file.file, instructions)
        if path is None:
            return render_400(request)
        name = attachment.name.rsplit('.', 1)[0]
        name = re.sub(r'[^\w\.\-]', '', name)
        pdf_file = File(open(path, 'rb'))
        if already:
            att = already
        else:
            att = FoiAttachment(
                belongs_to=attachment.belongs_to,
                name=_('%s_redacted.pdf') % name,
                is_redacted=True,
                filetype='application/pdf',
                approved=True,
                can_approve=True
            )
        att.file = pdf_file
        att.size = pdf_file.size
        att.approve_and_save()
        if not attachment.is_redacted:
            attachment.redacted = att
            attachment.can_approve = False
            attachment.approved = False
            attachment.save()
        return JsonResponse({'url': att.get_anchor_url()})
    return render(request, 'foirequest/redact.html', {
        'foirequest': foirequest,
        'attachment': attachment
    })
