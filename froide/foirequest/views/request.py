from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404

from froide.helper.utils import render_403

from ..models import FoiRequest, FoiEvent, FoiAttachment


def shortlink(request, obj_id):
    foirequest = get_object_or_404(FoiRequest, pk=obj_id)
    if foirequest.is_visible(request.user):
        return redirect(foirequest)
    else:
        return render_403(request)


def auth(request, obj_id, code):
    foirequest = get_object_or_404(FoiRequest, pk=obj_id)
    if foirequest.is_visible(request.user):
        return redirect(foirequest)
    if foirequest.check_auth_code(code):
        request.session['pb_auth'] = code
        return redirect(foirequest)
    else:
        return render_403(request)


def show(request, slug, template_name="foirequest/show.html",
            context=None, status=200):
    try:
        obj = FoiRequest.objects.select_related("public_body",
                "user", "law").get(slug=slug)
    except FoiRequest.DoesNotExist:
        raise Http404
    if not obj.is_visible(request.user, pb_auth=request.session.get('pb_auth')):
        return render_403(request)
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
    if request.user.is_authenticated and request.user == obj.user:
        if obj.awaits_classification():
            active_tab = 'set-status'
        elif obj.is_overdue() and obj.awaits_response():
            active_tab = 'write-message'

        if 'postal_reply_form' in context:
            active_tab = 'add-postal-reply'
        elif 'postal_message_form' in context:
            active_tab = 'add-postal-message'
        elif 'status_form' in context:
            active_tab = 'set-status'
        elif 'send_message_form' in context:
            active_tab = 'write-message'
        elif 'escalation_form' in context:
            active_tab = 'escalate'

    context.update({
        "object": obj,
        "active_tab": active_tab
    })
    return render(request, template_name, context, status=status)
