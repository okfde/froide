from __future__ import unicode_literals

from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext_lazy as _
from django.http import Http404
from django.contrib import messages

from froide.helper.utils import render_400

from ..models import FoiMessage
from ..forms import (SendMessageForm, PostalReplyForm, PostalMessageForm,
        PostalAttachmentForm, MessagePublicBodySenderForm,
        EscalationMessageForm)
from ..utils import check_throttle

from .request import show_foirequest
from .request_actions import allow_write_foirequest


@require_POST
@allow_write_foirequest
def send_message(request, foirequest):
    form = SendMessageForm(foirequest, request.POST)

    throttle_message = check_throttle(foirequest.user, FoiMessage)
    if throttle_message:
        form.add_error(None, throttle_message)

    if form.is_valid():
        mes = form.save(foirequest.user)
        messages.add_message(request, messages.SUCCESS,
                _('Your Message has been sent.'))
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
    form = EscalationMessageForm(foirequest, request.POST)

    throttle_message = check_throttle(foirequest.user, FoiMessage)
    if throttle_message:
        form.add_error(None, throttle_message)

    if form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your Escalation Message has been sent.'))
        return redirect(foirequest)
    else:
        return show_foirequest(request, foirequest, context={
            "escalation_form": form
        }, status=400)


@require_POST
@allow_write_foirequest
def add_postal_reply(request, foirequest, form_class=PostalReplyForm,
            success_message=_('A postal reply was successfully added!'),
            error_message=_('There were errors with your form submission!'),
            form_key='postal_reply_form', form_prefix='reply'):
    if not foirequest.public_body:
        return render_400(request)
    form = form_class(request.POST, request.FILES, foirequest=foirequest,
                      prefix=form_prefix)
    if form.is_valid():
        message = form.save()
        messages.add_message(request, messages.SUCCESS, success_message)
        return redirect(message)
    messages.add_message(request, messages.ERROR, error_message)
    return show_foirequest(request, foirequest, context={
        form_key: form
    }, status=400)


def add_postal_message(request, slug):
    return add_postal_reply(
        request,
        slug,
        form_class=PostalMessageForm,
        success_message=_('A sent letter was successfully added!'),
        error_message=_('There were errors with your form submission!'),
        form_key='postal_message_form', form_prefix='message'
    )


@require_POST
@allow_write_foirequest
def add_postal_reply_attachment(request, foirequest, message_id):
    try:
        message = FoiMessage.objects.get(request=foirequest, pk=int(message_id))
    except (ValueError, FoiMessage.DoesNotExist):
        raise Http404
    if not message.is_postal:
        return render_400(request)
    form = PostalAttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        result = form.save(message)
        added, updated = result
        if updated > 0 and not added:
            status_message = _('You updated %d document(s) on this message') % updated
        elif updated > 0 and added > 0:
            status_message = _('You added %(added)d and updated %(updated)d document(s) on this message') % {
                    'updated': updated, 'added': added
                    }
        elif added > 0:
            status_message = _('You added %d document(s) to this message.') % added
        messages.add_message(request, messages.SUCCESS, status_message)
        return redirect(message)
    messages.add_message(request, messages.ERROR,
            form._errors['files'][0])
    return render_400(request)


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
    form = MessagePublicBodySenderForm(message, request.POST)
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
        mes = FoiMessage.objects.get(sent=False, request=foirequest, pk=int(request.POST.get('message', 0)))
    except (FoiMessage.DoesNotExist, ValueError):
        messages.add_message(request, messages.ERROR,
                    _('Invalid input!'))
        return render_400(request)
    mes.send(notify=False)
    return redirect('admin:foirequest_foimessage_change', mes.id)
