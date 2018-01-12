from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404

from froide.helper.utils import render_403

from ..models import FoiRequest, FoiEvent, FoiAttachment
from ..auth import (can_read_foirequest, can_write_foirequest,
    check_foirequest_auth_code)


def shortlink(request, obj_id):
    foirequest = get_object_or_404(FoiRequest, pk=obj_id)
    if not can_read_foirequest(foirequest, request):
        return render_403(request)
    return redirect(foirequest)


def auth(request, obj_id, code):
    foirequest = get_object_or_404(FoiRequest, pk=obj_id)
    if can_read_foirequest(foirequest, request):
        return redirect(foirequest)
    if check_foirequest_auth_code(foirequest, code):
        request.session['pb_auth'] = code
        return redirect(foirequest)
    else:
        return render_403(request)


def show(request, slug, **kwargs):
    try:
        obj = FoiRequest.objects.select_related("public_body",
                "user", "law").get(slug=slug)
    except FoiRequest.DoesNotExist:
        raise Http404

    if not can_read_foirequest(obj, request):
        return render_403(request)

    return show_foirequest(request, obj, **kwargs)


def show_foirequest(request, obj, template_name="foirequest/show.html",
        context=None, status=200):
    all_attachments = FoiAttachment.objects.select_related('redacted')\
            .filter(belongs_to__request=obj).all()
    for message in obj.messages:
        message.request = obj
        if message.not_publishable:
            obj.not_publishable_message = message
        message.all_attachments = [a for a in all_attachments
                    if a.belongs_to_id == message.id]
        message.approved_attachments = [a for a in all_attachments
                    if a.belongs_to_id == message.id and a.approved]
        message.not_approved_attachments = [a for a in all_attachments
                    if a.belongs_to_id == message.id and not a.approved]

        for att in message.all_attachments:
            att.belongs_to = message

    events = FoiEvent.objects.filter(request=obj).select_related(
            "user", "request",
            "public_body").order_by("timestamp")

    event_count = len(events)
    last_index = event_count
    for message in reversed(obj.messages):
        message.events = [ev for ev in events[:last_index]
                if ev.timestamp >= message.timestamp]
        last_index = last_index - len(message.events)

    if context is None:
        context = {}

    active_tab = 'info'
    if can_write_foirequest(obj, request):
        active_tab = get_active_tab(obj, context)

    context.update({
        "object": obj,
        "active_tab": active_tab
    })
    return render(request, template_name, context, status=status)


def get_active_tab(obj, context):
    if obj.awaits_classification():
        return 'set-status'
    elif obj.is_overdue() and obj.awaits_response():
        return 'write-message'

    if 'postal_reply_form' in context:
        return 'add-postal-reply'
    elif 'postal_message_form' in context:
        return 'add-postal-message'
    elif 'status_form' in context:
        return 'set-status'
    elif 'send_message_form' in context:
        return 'write-message'
    elif 'escalation_form' in context:
        return 'escalate'
    return 'info'
