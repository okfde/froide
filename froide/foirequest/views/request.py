from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.utils.translation import gettext as _

from froide.helper.utils import render_403

from ..models import FoiRequest, FoiEvent, FoiAttachment
from ..forms.preferences import request_page_tour_pref
from ..auth import (can_read_foirequest, can_write_foirequest,
    check_foirequest_auth_code)


def shortlink(request, obj_id, url_path=''):
    foirequest = get_object_or_404(FoiRequest, pk=obj_id)
    if not can_read_foirequest(foirequest, request):
        return render_403(request)
    url = foirequest.get_absolute_url()
    if url_path:
        url_path = url_path[1:]
    return redirect(url + url_path)


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
        message.can_edit_attachments = bool([
            a for a in message.listed_attachments
            if a.can_edit
        ])
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
        "active_tab": active_tab,
        "preferences": {}
    })
    if can_write:
        context.update({
            "preferences": {
                "request_page_tour": request_page_tour_pref.get(request.user)
            }
        })

        if not context['preferences']['request_page_tour'].value:
            context.update({
                'tour_data': get_tour_data()
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


def get_tour_data():
    return {
        'i18n': {
            'done': _('👋 Goodbye!'),
            'next': _('Next'),
            'previous': _('Previous'),
            'close': _('Close'),
            'start': _('Next'),
        },
        'steps': [{
            'element': '#infobox',
            'popover': {
                'title': _('Status of request'),
                'description': _('''Here you can see the status and other details of your request. Under "Edit request status" you can update the status after you get a response.'''),
                'position': 'top'
            }
        }, {
            'element': '#correspondence-tab',
            'popover': {
                'title': _('Messages in this request'),
                'description': _('''Below you find all messages that you sent and received in this request. When you receive a response it appears at the end and we let you know about it via email.'''),
                'position': 'top'
            }
        }, {
            'element': '.upload-post-link',
            'popover': {
                'title': _('Got postal mail?'),
                'description': _('''When you receive a letter, you can click this button and upload a scan or photo of the letter. You can redact parts of the letter with our tool before publishing it.'''),
                'position': 'top'
            }
        }, {
            'element': '.write-message-top-link',
            'popover': {
                'title': _('Need to reply or send a reminder?'),
                'description': _('''This button takes you to the send message form. Let's go there next!'''),
                'position': 'top'
            }
        }, {
            'element': '#write-message .form-group',
            'popover': {
                'title': _('Sending messages'),
                'description': _('''You can reply to messages or send reminders about your request at the bottom of the page. If your request is refused or overdue you will be able to ask for mediation.'''),
                'position': 'top'
            }
        }, {
            'element': '#request-summary',
            'popover': {
                'title': _('Got the information you asked for?'),
                'description': _('''When you received documents, you can write a summary of what you have learned.'''),
            }
        }, {
            'element': '.request-section-header',
            'popover': {
                'title': _('The end.'),
                'description': _('''That concludes this tour! We'll let you know via email if anything around your request changes.'''),
                'position': 'top-center'
            }
        },
        ]
    }
