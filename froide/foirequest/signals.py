from typing import List, Optional

from django.db.models import signals
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from froide.helper.email_sending import mail_registry
from froide.helper.signals import email_left_queue

from .consumers import MESSAGEEDIT_ROOM_PREFIX
from .models import (
    DeliveryStatus,
    FoiAttachment,
    FoiEvent,
    FoiMessage,
    FoiProject,
    FoiRequest,
)
from .models.message import MESSAGE_ID_PREFIX
from .utils import send_request_user_email, short_request_url

became_overdue_email = mail_registry.register(
    "foirequest/emails/became_overdue",
    (
        "action_url",
        "upload_action_url",
        "write_action_url",
        "status_action_url",
        "foirequest",
        "user",
    ),
)
became_asleep_email = mail_registry.register(
    "foirequest/emails/became_asleep",
    (
        "action_url",
        "upload_action_url",
        "write_action_url",
        "status_action_url",
        "foirequest",
        "user",
    ),
)
message_received_email = mail_registry.register(
    "foirequest/emails/message_received_notification",
    ("action_url", "foirequest", "publicbody", "message", "user"),
)
public_body_suggested_email = mail_registry.register(
    "foirequest/emails/public_body_suggestion_received",
    ("action_url", "foirequest", "suggestion", "user"),
)
confirm_foi_project_created_email = mail_registry.register(
    "foirequest/emails/confirm_foi_project_created",
    ("foiproject", "action_url", "user"),
)
confirm_foi_request_sent_email = mail_registry.register(
    "foirequest/emails/confirm_foi_request_sent",
    ("foirequest", "message", "publicbody", "action_url", "upload_action_url", "user"),
)
confirm_foi_message_sent_email = mail_registry.register(
    "foirequest/emails/confirm_foi_message_sent",
    ("foirequest", "message", "publicbody", "action_url", "upload_action_url", "user"),
)


def trigger_index_update(klass, instance_pk):
    """Trigger index update by save"""
    try:
        obj = klass.objects.get(pk=instance_pk)
    except klass.DoesNotExist:
        return
    obj.save()


@receiver(FoiRequest.became_overdue, dispatch_uid="send_notification_became_overdue")
def send_notification_became_overdue(sender, **kwargs):
    req_url = sender.user.get_autologin_url(sender.get_absolute_short_url())
    upload_url = sender.user.get_autologin_url(
        short_request_url("foirequest-upload_postal_message_create", sender)
    )
    send_request_user_email(
        became_overdue_email,
        sender,
        subject=_("Request became overdue"),
        context={
            "foirequest": sender,
            "user": sender.user,
            "action_url": req_url,
            "upload_action_url": upload_url,
            "write_action_url": req_url + "#write-message",
            "status_action_url": req_url + "#set-status",
        },
        priority=False,
    )


@receiver(FoiRequest.became_asleep, dispatch_uid="send_notification_became_asleep")
def send_notification_became_asleep(sender, **kwargs):
    req_url = sender.user.get_autologin_url(sender.get_absolute_short_url())
    upload_url = sender.user.get_autologin_url(
        short_request_url("foirequest-upload_postal_message_create", sender)
    )

    send_request_user_email(
        became_asleep_email,
        sender,
        subject=_("Request became asleep"),
        context={
            "foirequest": sender,
            "user": sender.user,
            "action_url": req_url,
            "upload_action_url": upload_url,
            "write_action_url": req_url + "#write-message",
            "status_action_url": req_url + "#set-status",
        },
        priority=False,
    )


@receiver(FoiRequest.message_received, dispatch_uid="notify_user_message_received")
def notify_user_message_received(sender, message=None, **kwargs):
    if kwargs.get("user") == sender.user:
        # If the same user has uploaded this, don't notify
        return

    send_request_user_email(
        message_received_email,
        sender,
        subject=_("New reply to your request"),
        context={
            "message": message,
            "foirequest": sender,
            "user": sender.user,
            "publicbody": message.sender_public_body,
            "action_url": sender.user.get_autologin_url(
                short_request_url("foirequest-edit_email_message", sender, message)
            ),
        },
        priority=False,
    )


@receiver(
    FoiRequest.public_body_suggested, dispatch_uid="notify_user_public_body_suggested"
)
def notify_user_public_body_suggested(sender, suggestion=None, **kwargs):
    if sender.user == suggestion.user:
        return

    send_request_user_email(
        public_body_suggested_email,
        sender,
        subject=_("New suggestion for a Public Body"),
        context={
            "suggestion": suggestion,
            "foirequest": sender,
            "user": sender.user,
            "action_url": sender.user.get_autologin_url(
                sender.get_absolute_short_url()
            ),
        },
        priority=False,
    )


@receiver(FoiRequest.message_sent, dispatch_uid="set_last_message_date_on_message_sent")
def set_last_message_date_on_message_sent(sender, message=None, **kwargs):
    if message is not None:
        sender.last_message = sender.messages[-1].timestamp
        sender.save()


@receiver(
    FoiRequest.message_received,
    dispatch_uid="set_last_message_date_on_message_received",
)
def set_last_message_date_on_message_received(sender, message=None, **kwargs):
    if message is not None:
        sender.last_message = sender.messages[-1].timestamp
        sender.save()


@receiver(
    FoiProject.project_created, dispatch_uid="send_foiproject_created_confirmation"
)
def send_foiproject_created_confirmation(sender, **kwargs):
    confirm_foi_project_created_email.send(
        user=sender.user,
        subject=_("Your Freedom of Information Project has been created"),
        context={
            "foiproject": sender,
            "user": sender.user,
            "action_url": sender.get_absolute_domain_short_url(),
        },
        priority=False,
    )


# Updating public body request counts
@receiver(
    FoiRequest.request_to_public_body, dispatch_uid="foirequest_increment_request_count"
)
def increment_request_count(sender, **kwargs):
    if not sender.public_body:
        return
    sender.public_body.number_of_requests += 1
    sender.public_body.save()


@receiver(
    signals.pre_delete,
    sender=FoiRequest,
    dispatch_uid="foirequest_decrement_request_count",
)
def decrement_request_count(sender, instance=None, **kwargs):
    if not instance.public_body:
        return
    instance.public_body.number_of_requests -= 1
    if instance.public_body.number_of_requests < 0:
        instance.public_body.number_of_requests = 0
    instance.public_body.save()


# Indexing


@receiver(
    signals.post_save, sender=FoiMessage, dispatch_uid="foimessage_delayed_update"
)
def foimessage_delayed_update(instance=None, created=False, **kwargs):
    if created and kwargs.get("raw", False):
        return
    trigger_index_update(FoiRequest, instance.request_id)


@receiver(
    signals.post_delete, sender=FoiMessage, dispatch_uid="foimessage_delayed_remove"
)
def foimessage_delayed_remove(instance, **kwargs):
    trigger_index_update(FoiRequest, instance.request_id)


@receiver(
    signals.post_save, sender=FoiAttachment, dispatch_uid="foiattachment_delayed_update"
)
def foiattachment_delayed_update(instance, created=False, **kwargs):
    if created and kwargs.get("raw", False):
        return
    trigger_index_update(FoiRequest, instance.belongs_to.request_id)


@receiver(
    signals.post_delete,
    sender=FoiAttachment,
    dispatch_uid="foiattachment_delayed_remove",
)
def foiattachment_delayed_remove(instance, **kwargs):
    try:
        has_request = instance.belongs_to.request_id is not None
        if instance.belongs_to is not None and has_request:
            trigger_index_update(FoiRequest, instance.belongs_to.request_id)
    except FoiMessage.DoesNotExist:
        pass


# Event creation


@receiver(FoiRequest.message_sent, dispatch_uid="create_event_message_sent")
def create_event_message_sent(sender, message, user=None, request=None, **kwargs):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.MESSAGE_SENT,
        sender,
        message=message,
        user=user,
        request=request,
        public_body=message.recipient_public_body,
    )


@receiver(FoiRequest.message_received, dispatch_uid="create_event_message_received")
def create_event_message_received(
    sender, message=None, user=None, request=None, **kwargs
):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.MESSAGE_RECEIVED,
        sender,
        message=message,
        user=user,
        request=request,
        public_body=message.sender_public_body,
    )


@receiver(
    FoiAttachment.attachment_approved,
    dispatch_uid="create_event_followers_attachments_approved",
)
def create_event_followers_attachments_approved(sender, user=None, **kwargs):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.ATTACHMENT_APPROVED,
        sender.belongs_to.request,
        user=user,
        attachment_id=sender.id,
    )


@receiver(
    FoiAttachment.attachment_redacted,
    dispatch_uid="create_event_followers_attachment_redacted",
)
def create_event_followers_attachments_redacted(sender, user=None, **kwargs):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.ATTACHMENT_REDACTED,
        sender.belongs_to.request,
        user=user,
        attachment_id=sender.id,
    )


@receiver(
    FoiAttachment.attachment_deleted,
    dispatch_uid="create_event_followers_attachment_deleted",
)
def create_event_followers_attachments_attachment_deleted(
    sender, user=None, request=None, **kwargs
):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.ATTACHMENT_DELETED,
        sender.belongs_to.request,
        user=user,
        request=request,
        attachment_id=sender.id,
    )


@receiver(
    FoiAttachment.document_created,
    dispatch_uid="create_event_followers_attachment_document_created",
)
def create_event_followers_attachments_document_created(
    sender, user=None, request=None, **kwargs
):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.DOCUMENT_CREATED,
        sender.belongs_to.request,
        user=user,
        request=request,
        attachment_id=sender.id,
    )


@receiver(
    FoiAttachment.attachment_available,
    dispatch_uid="broadcast_attachment_available",
)
def broadcast_attachment_available(sender, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        MESSAGEEDIT_ROOM_PREFIX.format(sender.belongs_to_id),
        {"type": "attachment_available", "attachment": sender.id},
    )


@receiver(FoiRequest.status_changed, dispatch_uid="create_event_status_changed")
def create_event_status_changed(sender, user=None, request=None, **kwargs):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.STATUS_CHANGED,
        sender,
        user=user,
        request=request,
        status=kwargs.get("status", ""),
        resolution=kwargs.get("resolution", ""),
        costs=kwargs["data"].get("costs"),
        previous_status=kwargs.get("previous_status", ""),
        previous_resolution=kwargs.get("previous_resolution", ""),
        refusal_reason=kwargs["data"].get("refusal_reason", ""),
    )


@receiver(FoiRequest.costs_reported, dispatch_uid="create_event_costs_reported")
def create_event_costs_reported(sender: FoiRequest, user=None, request=None, **kwargs):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.REPORTED_COSTS,
        sender,
        user=user,
        request=request,
        costs=kwargs.get("costs"),
    )


@receiver(FoiRequest.made_public, dispatch_uid="create_event_made_public")
def create_event_made_public(sender, user=None, request=None, **kwargs):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.MADE_PUBLIC, sender, user=user, request=request
    )


@receiver(
    FoiRequest.public_body_suggested, dispatch_uid="create_event_public_body_suggested"
)
def create_event_public_body_suggested(sender, suggestion=None, **kwargs):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.PUBLIC_BODY_SUGGESTED,
        sender,
        user=suggestion.user,
        public_body=suggestion.public_body,
    )


@receiver(FoiRequest.became_overdue, dispatch_uid="create_event_became_overdue")
def create_event_became_overdue(sender, **kwargs):
    FoiEvent.objects.create_event(FoiEvent.EVENTS.BECAME_OVERDUE, sender)


@receiver(FoiRequest.set_concrete_law, dispatch_uid="create_event_set_concrete_law")
def create_event_set_concrete_law(sender, user=None, **kwargs):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.SET_CONCRETE_LAW, sender, user=user, name=kwargs["name"]
    )


@receiver(FoiRequest.escalated, dispatch_uid="create_event_escalated")
def create_event_escalated(sender, message=None, user=None, **kwargs):
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.ESCALATED,
        sender,
        message=message,
        user=user,
        public_body=message.recipient_public_body,
    )


def pre_comment_foimessage(sender=None, comment=None, request=None, **kwargs):
    from .models import FoiMessage

    if comment.content_type.model_class() != FoiMessage:
        return

    user = request.user
    if not user.is_authenticated:
        return False

    foimessage = comment.content_object
    foirequest = foimessage.request

    # Do not store email or URL
    comment.user_email = ""
    comment.user_url = ""

    # Use requester when private on own request
    if user.private and foirequest.user == user:
        comment.user_name = str(_("requester"))
    return True


@receiver(email_left_queue)
def save_delivery_status(
    message_id: Optional[str], status: str, log: List[str], **kwargs
):
    from froide.problem.models import ProblemReport

    if message_id is None or not message_id.startswith("<{}".format(MESSAGE_ID_PREFIX)):
        return

    try:
        message = FoiMessage.objects.filter(email_message_id=message_id).get()
    except FoiMessage.DoesNotExist:
        return

    delivery_status, _ = DeliveryStatus.objects.update_or_create(
        message=message,
        defaults={
            "log": "".join(log),
            "status": status,
            "last_update": timezone.now(),
        },
    )

    if status == "sent":
        send_foimessage_sent_confirmation(message)
    elif delivery_status.is_failed():
        if not ProblemReport.objects.filter(
            message=message, kind=ProblemReport.PROBLEM.BOUNCE_PUBLICBODY
        ).exists():
            ProblemReport.objects.report(
                message=message,
                kind=ProblemReport.PROBLEM.BOUNCE_PUBLICBODY,
                description=delivery_status.log,
                auto_submitted=True,
            )


def send_foimessage_sent_confirmation(message: FoiMessage = None, **kwargs):
    request = message.request
    if message.is_not_email:
        # All non-email sent messages are not interesting to users.
        # Don't inform them about it.
        return
    if message.is_bulk:
        # Don't notify on bulk message sending
        return

    if message.confirmation_sent:
        # Don't send a second confirmation for this message
        return

    messages = request.get_messages()
    start_thread = False
    if len(messages) >= 1 and message == messages[0]:
        if request.project_id is not None:
            # Don't notify on first message in a project
            return
        subject = _("Your Freedom of Information Request was sent")
        mail_intent = confirm_foi_request_sent_email
        action_url = request.get_absolute_domain_short_url()
        start_thread = True
    else:
        subject = _("Your message was sent")
        mail_intent = confirm_foi_message_sent_email
        action_url = message.get_absolute_domain_short_url()

    upload_url = request.user.get_autologin_url(
        short_request_url("foirequest-upload_postal_message_create", request)
    )

    context = {
        "foirequest": request,
        "user": request.user,
        "publicbody": message.recipient_public_body,
        "message": message,
        "action_url": action_url,
        "upload_action_url": upload_url,
    }

    send_request_user_email(
        mail_intent,
        request,
        subject=subject,
        context=context,
        start_thread=start_thread,
    )

    message.confirmation_sent = True
    message.save(update_fields=["confirmation_sent"])


@receiver(
    signals.post_save, sender=FoiAttachment, dispatch_uid="broadcast_attachment_added"
)
def broadcast_attachment_added(instance, created=False, **kwargs):
    if not created or kwargs.get("raw", False):
        return
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        MESSAGEEDIT_ROOM_PREFIX.format(instance.belongs_to_id),
        {"type": "attachment_added", "attachment": instance.id},
    )
