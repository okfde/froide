from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.generic import DetailView

from froide.account.preferences import get_preferences_for_user
from froide.helper.utils import render_403

from ..auth import can_read_foirequest, can_write_foirequest, check_foirequest_auth_code
from ..forms.preferences import message_received_tour_pref, request_page_tour_pref
from ..models import FoiAttachment, FoiEvent, FoiRequest


def shortlink(request, obj_id, url_path=""):
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
        request.session["pb_auth"] = code
        return redirect(foirequest)
    if can_read_foirequest(foirequest, request):
        return redirect(foirequest)
    return render_403(request)


def can_see_attachment(att, can_write):
    if att.approved:
        return True
    if att.redacted_id and not can_write:
        return False
    if att.converted_id and not can_write:
        return False
    return True


def show_foirequest(
    request, obj, template_name="foirequest/show.html", context=None, status=200
):

    if context is None:
        context = {}

    context.update(get_foirequest_context(request, obj))

    return render(request, template_name, context, status=status)


class FoiRequestView(DetailView):
    queryset = FoiRequest.objects.select_related(
        "public_body",
        "jurisdiction",
        "user",
        "law",
    ).prefetch_related(
        "tags",
    )
    template_name = "foirequest/show.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not can_read_foirequest(self.object, self.request):
            return render_403(self.request)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        obj = self.object
        request = self.request

        context.update(get_foirequest_context(request, obj))

        return context


def get_foirequest_context(request, obj):
    context = {}

    all_attachments = FoiAttachment.objects.select_related("redacted").filter(
        belongs_to__request=obj
    )

    can_write = can_write_foirequest(obj, request)

    messages = obj.get_messages(with_tags=can_write)

    for message in messages:
        message.request = obj
        message.all_attachments = [
            a for a in all_attachments if a.belongs_to_id == message.id
        ]

        # Preempt attribute access
        for att in message.all_attachments:
            att.belongs_to = message

        message.listed_attachments = [
            a
            for a in all_attachments
            if a.belongs_to_id == message.id and can_see_attachment(a, can_write)
        ]
        message.hidden_attachments = [
            a for a in message.listed_attachments if a.is_irrelevant
        ]
        message.can_edit_attachments = bool(
            [a for a in message.listed_attachments if a.can_edit]
        )
        message.approved_attachments = [
            a
            for a in message.listed_attachments
            if a.approved and a not in message.hidden_attachments
        ]
        message.unapproved_attachments = [
            a
            for a in message.listed_attachments
            if not a.approved and a not in message.hidden_attachments
        ]

    events = (
        FoiEvent.objects.filter(request=obj)
        .select_related("user", "request", "public_body")
        .order_by("timestamp")
    )

    event_count = len(events)
    last_index = event_count
    for message in reversed(obj.messages):
        message.events = [
            ev for ev in events[:last_index] if ev.timestamp >= message.timestamp
        ]
        last_index = last_index - len(message.events)

    # TODO: remove active_tab
    active_tab = "info"
    if can_write:
        active_tab = get_active_tab(obj, context)

    context.update({"object": obj, "active_tab": active_tab, "preferences": {}})
    if can_write:
        preferences = get_preferences_for_user(
            request.user, [request_page_tour_pref, message_received_tour_pref]
        )
        context.update({"preferences": preferences})

        if (
            obj.reply_received()
            and not preferences["foirequest_messagereceived_tour"].value
        ):
            context.update(
                {"foirequest_messagereceived_tour": get_messagereceived_tour_data()}
            )
        elif not preferences["foirequest_requestpage_tour"].value:
            context.update({"foirequest_requestpage_tour": get_requestpage_tour_data()})
    return context


def get_active_tab(obj, context):
    if "postal_reply_form" in context:
        return "add-postal-reply"
    elif "postal_message_form" in context:
        return "add-postal-message"
    elif "status_form" in context:
        return "set-status"
    elif "send_message_form" in context:
        return "write-message"
    elif "escalation_form" in context:
        return "escalate"

    if "active_tab" in context:
        return context["active_tab"]

    if obj.awaits_classification():
        return "set-status"
    elif obj.is_overdue() and obj.awaits_response():
        return "write-message"

    return "info"


def get_base_tour_data():
    return {
        "i18n": {
            "done": _("👋 Goodbye!"),
            "next": _("Next"),
            "previous": _("Previous"),
            "close": _("Close"),
            "start": _("Next"),
        }
    }


def get_requestpage_tour_data():
    return {
        **get_base_tour_data(),
        "steps": [
            {
                "element": "#infobox .info-box__header",
                "popover": {
                    "title": _("Status of request"),
                    "description": _(
                        """Here you can see the status your request. Below you can update the status of your request when you receive a response."""
                    ),
                },
            },
            {
                "element": "#due-date",
                "popover": {
                    "title": _("Deadline"),
                    "description": _(
                        """This is the deadline for your request. If the public body has not replied by then, we will let you know, so you can send a reminder. You can also adjust the date if necessary."""
                    ),
                },
            },
            {
                "element": "#share-links",
                "popover": {
                    "title": _("Share links"),
                    "description": _(
                        """Here are some quick links for you to share your request with others."""
                    ),
                },
            },
            {
                "element": "#download-links",
                "popover": {
                    "title": _("Download"),
                    "description": _(
                        """You can download all messages of your request. The RSS link allows you to subscribe to the request in a feed reader."""
                    ),
                },
            },
            {
                "element": "#correspondence-tab",
                "popover": {
                    "title": _("Messages in this request"),
                    "description": _(
                        """Below you find all messages that you sent and received in this request. When you receive a response it appears at the end and we let you know about it via email."""
                    ),
                },
            },
            {
                "element": "#correspondence .alpha-message .alpha-message__head",
                "popover": {
                    "title": _("Details of your message"),
                    "description": _(
                        """This is your message. There's more information e.g. about the delivery status of your message when you click on the “Details” link."""
                    ),
                },
                "position": "top-center",
            },
            {
                "element": ".write-message-top-link",
                "popover": {
                    "title": _("Need to reply or send a reminder?"),
                    "description": _(
                        """This button takes you to the send message form."""
                    ),
                },
            },
            {
                "element": ".upload-post-link",
                "popover": {
                    "title": _("Got postal mail?"),
                    "description": _(
                        """When you receive a letter, you can click this button and upload a scan or photo of the letter. You can redact parts of the letter with our tool before publishing it."""
                    ),
                },
            },
            {
                "element": ".request-title",
                "popover": {
                    "title": _("The end."),
                    "description": _(
                        """That concludes this tour! We'll let you know via email if anything around your request changes."""
                    ),
                    "position": "top-center",
                },
            },
        ],
    }


def get_messagereceived_tour_data():
    return {
        **get_base_tour_data(),
        "steps": [
            {
                "element": "#infobox .info-box__header",
                "popover": {
                    "title": _("Status of request"),
                    "description": _(
                        """After you read your replies you need to update the status of your request here below."""
                    ),
                },
            },
            {
                "element": "#correspondence .alpha-message",
                "popover": {
                    "title": _("Message toolbar"),
                    "description": _(
                        """The “Redact” button allows you to redact the text of a message in case sensitive information is accidentally not automatically removed. The “Problem?” allows you to notify our moderation team, if you have a problem with a message."""
                    ),
                    "position": "bottom-center",
                },
            },
            {
                "element": ".reply-form__wrap",
                "popover": {
                    "title": _("Reply"),
                    "description": _(
                        """At the bottom of the page you can send replies to the public body or start a mediation process with the mediation authority."""
                    ),
                    "position": "top-center",
                },
            },
            {
                "element": "#request-summary",
                "popover": {
                    "title": _("Got the information you asked for?"),
                    "description": _(
                        """When you received documents, you can write a summary of what you have learned."""
                    ),
                },
            },
            {
                "element": ".request-title",
                "popover": {
                    "title": _("The end."),
                    "description": _("""That concludes this tour!"""),
                    "position": "top-center",
                },
            },
        ],
    }
