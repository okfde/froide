from django.db.models import signals
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from froide.helper.email_sending import mail_registry

from .models import FoiRequest, FoiMessage, FoiAttachment, FoiEvent, FoiProject
from .utils import send_request_user_email


became_overdue_email = mail_registry.register(
    'foirequest/emails/became_overdue',
    ('action_url', 'foirequest',)
)
became_asleep_email = mail_registry.register(
    'foirequest/emails/became_asleep',
    ('action_url', 'foirequest',)
)
message_received_email = mail_registry.register(
    'foirequest/emails/message_received_notification',
    ('action_url', 'foirequest', 'publicbody', 'message')
)
public_body_suggested_email = mail_registry.register(
    'foirequest/emails/public_body_suggestion_received',
    ('action_url', 'foirequest', 'suggestion')
)
confirm_foi_project_created_email = mail_registry.register(
    'foirequest/emails/confirm_foi_project_created',
    ('foirequest',)
)
confirm_foi_request_sent_email = mail_registry.register(
    'foirequest/emails/confirm_foi_request_sent',
    ('foirequest', 'message', 'publicbody')
)
confirm_foi_message_sent_email = mail_registry.register(
    'foirequest/emails/confirm_foi_message_sent',
    ('foirequest', 'message', 'publicbody')
)


def trigger_index_update(klass, instance_pk):
    """ Trigger index update by save """
    try:
        obj = klass.objects.get(pk=instance_pk)
    except klass.DoesNotExist:
        return
    obj.save()


@receiver(FoiRequest.became_overdue,
        dispatch_uid="send_notification_became_overdue")
def send_notification_became_overdue(sender, **kwargs):
    send_request_user_email(
        became_overdue_email,
        sender,
        subject=_("Request became overdue"),
        context={
            "foirequest": sender,
            "action_url": sender.user.get_autologin_url(sender.get_absolute_short_url()),
        },
        priority=False
    )


@receiver(FoiRequest.became_asleep,
        dispatch_uid="send_notification_became_asleep")
def send_notification_became_asleep(sender, **kwargs):
    send_request_user_email(
        became_asleep_email,
        sender,
        subject=_("Request became asleep"),
        context={
            "foirequest": sender,
            "action_url": sender.user.get_autologin_url(
                sender.get_absolute_short_url()
            ),
        },
        priority=False
    )


@receiver(FoiRequest.message_received,
        dispatch_uid="notify_user_message_received")
def notify_user_message_received(sender, message=None, **kwargs):
    if message.kind not in ('email', 'upload'):
        # All non-email/upload received messages the user actively contributed
        # Don't inform them about it
        return

    send_request_user_email(
        message_received_email,
        sender,
        subject=_("New reply to your request"),
        context={
            "message": message,
            "foirequest": sender,
            "publicbody": message.sender_public_body,
            "action_url": sender.user.get_autologin_url(
                message.get_absolute_short_url()
            )
        },
        priority=False
    )


@receiver(FoiRequest.public_body_suggested,
        dispatch_uid="notify_user_public_body_suggested")
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
            "action_url": sender.user.get_autologin_url(
                sender.get_absolute_short_url()
            )
        },
        priority=False
    )


@receiver(FoiRequest.message_sent,
        dispatch_uid="set_last_message_date_on_message_sent")
def set_last_message_date_on_message_sent(sender, message=None, **kwargs):
    if message is not None:
        sender.last_message = sender.messages[-1].timestamp
        sender.save()


@receiver(FoiRequest.message_received,
        dispatch_uid="set_last_message_date_on_message_received")
def set_last_message_date_on_message_received(sender, message=None, **kwargs):
    if message is not None:
        sender.last_message = sender.messages[-1].timestamp
        sender.save()


@receiver(FoiProject.project_created,
        dispatch_uid="send_foiproject_created_confirmation")
def send_foiproject_created_confirmation(sender, **kwargs):
    confirm_foi_project_created_email.send(
        user=sender.user,
        subject=_("Your Freedom of Information Project has been created"),
        context={
            "foirequest": sender
        },
        priority=False,
    )


@receiver(FoiRequest.message_sent,
        dispatch_uid="send_foimessage_sent_confirmation")
def send_foimessage_sent_confirmation(sender, message=None, **kwargs):
    if message.kind != 'email':
        # All non-email sent messages are not interesting to users.
        # Don't inform them about it.
        return

    messages = sender.get_messages()
    if len(messages) == 1:
        if sender.project_id is not None:
            return
        subject = _("Your Freedom of Information Request was sent")
        mail_intent = confirm_foi_request_sent_email
    else:
        subject = _("Your message was sent")
        mail_intent = confirm_foi_message_sent_email

    context = {
        "foirequest": sender,
        "publicbody": message.recipient_public_body,
        "message": message,
    }

    send_request_user_email(
        mail_intent,
        sender,
        subject=subject,
        context=context
    )


# Updating public body request counts
@receiver(FoiRequest.request_to_public_body,
        dispatch_uid="foirequest_increment_request_count")
def increment_request_count(sender, **kwargs):
    if not sender.public_body:
        return
    sender.public_body.number_of_requests += 1
    sender.public_body.save()


@receiver(signals.pre_delete, sender=FoiRequest,
        dispatch_uid="foirequest_decrement_request_count")
def decrement_request_count(sender, instance=None, **kwargs):
    if not instance.public_body:
        return
    instance.public_body.number_of_requests -= 1
    if instance.public_body.number_of_requests < 0:
        instance.public_body.number_of_requests = 0
    instance.public_body.save()


# Indexing

@receiver(signals.post_save, sender=FoiMessage,
        dispatch_uid='foimessage_delayed_update')
def foimessage_delayed_update(instance=None, created=False, **kwargs):
    if created and kwargs.get('raw', False):
        return
    trigger_index_update(FoiRequest, instance.request_id)


@receiver(signals.post_delete, sender=FoiMessage,
        dispatch_uid='foimessage_delayed_remove')
def foimessage_delayed_remove(instance, **kwargs):
    trigger_index_update(FoiRequest, instance.request_id)


@receiver(signals.post_save, sender=FoiAttachment,
        dispatch_uid='foiattachment_delayed_update')
def foiattachment_delayed_update(instance, created=False, **kwargs):
    if created and kwargs.get('raw', False):
        return
    trigger_index_update(FoiRequest, instance.belongs_to.request_id)


@receiver(signals.post_delete, sender=FoiAttachment,
        dispatch_uid='foiattachment_delayed_remove')
def foiattachment_delayed_remove(instance, **kwargs):
    try:
        has_request = instance.belongs_to.request_id is not None
        if instance.belongs_to is not None and has_request:
            trigger_index_update(FoiRequest, instance.belongs_to.request_id)
    except FoiMessage.DoesNotExist:
        pass


# Event creation

@receiver(FoiRequest.message_sent, dispatch_uid="create_event_message_sent")
def create_event_message_sent(sender, message, **kwargs):
    FoiEvent.objects.create_event(
        "message_sent",
        sender,
        user=sender.user,
        public_body=message.recipient_public_body
    )


@receiver(FoiRequest.message_received,
        dispatch_uid="create_event_message_received")
def create_event_message_received(sender, message=None, **kwargs):
    FoiEvent.objects.create_event(
        "message_received",
        sender,
        user=sender.user,
        public_body=message.sender_public_body
    )


@receiver(FoiAttachment.attachment_published,
    dispatch_uid="create_event_followers_attachments_approved")
def create_event_followers_attachments_approved(sender, **kwargs):
    FoiEvent.objects.create_event(
        "attachment_published",
        sender.belongs_to.request,
        user=sender.belongs_to.request.user,
        public_body=sender.belongs_to.request.public_body
    )


@receiver(FoiRequest.status_changed,
        dispatch_uid="create_event_status_changed")
def create_event_status_changed(sender, **kwargs):
    resolution = kwargs['resolution']
    data = kwargs['data']
    if data.get('costs', 0) > 0:
        FoiEvent.objects.create_event("reported_costs", sender,
                user=sender.user,
                public_body=sender.public_body, amount=data['costs'])
    elif resolution == "refused" and data['refusal_reason']:
        FoiEvent.objects.create_event("request_refused", sender,
                user=sender.user,
                public_body=sender.public_body, reason=data['refusal_reason'])
    elif resolution == "partially_successful" and data['refusal_reason']:
        FoiEvent.objects.create_event("partially_successful", sender,
                user=sender.user,
                public_body=sender.public_body, reason=data['refusal_reason'])
    else:
        FoiEvent.objects.create_event("status_changed", sender, user=sender.user,
            public_body=sender.public_body,
            status=FoiRequest.get_readable_status(resolution))


@receiver(FoiRequest.made_public,
        dispatch_uid="create_event_made_public")
def create_event_made_public(sender, **kwargs):
    FoiEvent.objects.create_event("made_public", sender, user=sender.user,
            public_body=sender.public_body)


@receiver(FoiRequest.public_body_suggested,
        dispatch_uid="create_event_public_body_suggested")
def create_event_public_body_suggested(sender, suggestion=None, **kwargs):
    FoiEvent.objects.create_event("public_body_suggested", sender, user=suggestion.user,
            public_body=suggestion.public_body)


@receiver(FoiRequest.became_overdue,
        dispatch_uid="create_event_became_overdue")
def create_event_became_overdue(sender, **kwargs):
    FoiEvent.objects.create_event("became_overdue", sender)


@receiver(FoiRequest.set_concrete_law,
        dispatch_uid="create_event_set_concrete_law")
def create_event_set_concrete_law(sender, **kwargs):
    FoiEvent.objects.create_event("set_concrete_law", sender,
            user=sender.user, name=kwargs['name'])


@receiver(FoiRequest.escalated,
    dispatch_uid="create_event_escalated")
def create_event_escalated(sender, **kwargs):
    FoiEvent.objects.create_event("escalated", sender,
            user=sender.user, public_body=sender.law.mediator)


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
    comment.user_email = ''
    comment.user_url = ''

    # Use full name, except when private on own request
    comment.user_name = user.get_full_name()
    if user.private and foirequest.user == user:
        comment.user_name = str(_('requester'))
    return True
