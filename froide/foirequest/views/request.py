from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404

from froide.helper.utils import render_403

from ..models import FoiRequest, FoiEvent, FoiAttachment
from ..auth import (can_read_foirequest, can_write_foirequest,
    check_foirequest_auth_code)


def shortlink(request, obj_id, url_part=''):
    foirequest = get_object_or_404(FoiRequest, pk=obj_id)
    if not can_read_foirequest(foirequest, request):
        return render_403(request)
    url = foirequest.get_absolute_url()
    return redirect(url + url_part)


def auth(request, obj_id, code):
    foirequest = get_object_or_404(FoiRequest, pk=obj_id)
    if check_foirequest_auth_code(foirequest, code):
        request.session['pb_auth'] = code
        return redirect(foirequest)
    if can_read_foirequest(foirequest, request):
        return redirect(foirequest)
    return render_403(request)


def show(request, slug, **kwargs):
    try:
        obj = FoiRequest.objects.select_related(
            "public_body",
            "jurisdiction",
            "user",
            "law",
        ).prefetch_related(
            "tags",
        ).get(slug=slug)
    except FoiRequest.DoesNotExist:
        raise Http404

    if not can_read_foirequest(obj, request):
        return render_403(request)

    return show_foirequest(request, obj, **kwargs)


def can_see_attachment(att, can_write):
    if att.approved:
        return True
    if att.redacted_id and not can_write:
        return False
    if att.converted_id and not can_write:
        return False
    return True


def show_foirequest(request, obj, template_name="foirequest/show.html",
        context=None, status=200):
    all_attachments = (
        FoiAttachment.objects
        .select_related('redacted')
        .filter(belongs_to__request=obj)
    )

    can_write = can_write_foirequest(obj, request)

    messages = obj.get_messages(with_tags=can_write)

    for message in messages:
        message.request = obj
        message.all_attachments = [a for a in all_attachments
                    if a.belongs_to_id == message.id]
        message.listed_attachments = [a for a in all_attachments
            if a.belongs_to_id == message.id and
            can_see_attachment(a, can_write)]
        message.hidden_attachments = [
            a for a in message.listed_attachments
            if a.is_irrelevant
        ]
        message.approved_attachments = [
            a for a in message.listed_attachments
            if a.approved and a not in message.hidden_attachments
        ]
        message.unapproved_attachments = [
            a for a in message.listed_attachments
            if not a.approved and a not in message.hidden_attachments
        ]

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
    if can_write:
        active_tab = get_active_tab(obj, context)

    context.update({
        "object": obj,
        "active_tab": active_tab
    })

    alpha_key = 'foirequest_alpha'
    alpha = request.GET.get('alpha')
    if alpha:
        if alpha == '1':
            request.session[alpha_key] = True
        elif alpha == '0' and alpha_key in request.session:
            del request.session[alpha_key]
        return redirect(obj)

    if alpha_key in request.session:
        template_name = [
            "foirequest/alpha/show.html",
            "foirequest/show.html"
        ]

    return render(request, template_name, context, status=status)


def get_active_tab(obj, context):
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

    if 'active_tab' in context:
        return context['active_tab']

    if obj.awaits_classification():
        return 'set-status'
    elif obj.is_overdue() and obj.awaits_response():
        return 'write-message'

    return 'info'
