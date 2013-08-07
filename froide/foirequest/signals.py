from django.db.models import signals
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from haystack.utils import get_identifier

from celery_haystack.utils import get_update_task

from .models import FoiRequest, FoiMessage, FoiAttachment, FoiEvent


def trigger_index_update(klass, instance_pk):
    task = get_update_task()
    task.delay('update', get_identifier(klass(id=instance_pk)))


@receiver(FoiRequest.became_overdue,
        dispatch_uid="send_notification_became_overdue")
def send_notification_became_overdue(sender, **kwargs):
    if not sender.user.is_active:
        return
    if not sender.user.email:
        return
    send_mail(_("%(site_name)s: Request became overdue")
                % {"site_name": settings.SITE_NAME},
            render_to_string("foirequest/emails/became_overdue.txt",
                {"request": sender,
                    "go_url": sender.user.get_profile().get_autologin_url(sender.get_absolute_short_url()),
                    "site_name": settings.SITE_NAME}),
            settings.DEFAULT_FROM_EMAIL,
            [sender.user.email])


@receiver(FoiRequest.became_asleep,
        dispatch_uid="send_notification_became_asleep")
def send_notification_became_asleep(sender, **kwargs):
    if not sender.user.is_active:
        return
    if not sender.user.email:
        return
    send_mail(_("%(site_name)s: Request became asleep")
                % {"site_name": settings.SITE_NAME},
            render_to_string("foirequest/emails/became_asleep.txt",
                {"request": sender,
                    "go_url": sender.user.get_profile().get_autologin_url(sender.get_absolute_short_url()),
                    "site_name": settings.SITE_NAME}),
            settings.DEFAULT_FROM_EMAIL,
            [sender.user.email])


@receiver(FoiRequest.message_received,
        dispatch_uid="notify_user_message_received")
def notify_user_message_received(sender, message=None, **kwargs):
    if not sender.user.is_active:
        return
    if not sender.user.email:
        return
    send_mail(_("You received a reply to your Freedom of Information Request"),
            render_to_string("foirequest/emails/message_received_notification.txt",
                {"message": message, "request": sender,
                    "go_url": sender.user.get_profile().get_autologin_url(message.get_absolute_short_url()),
                    "site_name": settings.SITE_NAME}),
            settings.DEFAULT_FROM_EMAIL,
            [sender.user.email])


@receiver(FoiRequest.public_body_suggested,
        dispatch_uid="notify_user_public_body_suggested")
def notify_user_public_body_suggested(sender, suggestion=None, **kwargs):
    if sender.user != suggestion.user:
        send_mail(_("Your request received a suggestion for a Public Body"),
                render_to_string("foirequest/emails/public_body_suggestion_received.txt",
                    {"suggestion": suggestion, "request": sender,
                    "go_url": sender.user.get_profile().get_autologin_url(
                            sender.get_absolute_short_url()),
                    "site_name": settings.SITE_NAME}),
                settings.DEFAULT_FROM_EMAIL,
                [sender.user.email])


@receiver(FoiRequest.message_sent,
        dispatch_uid="send_foimessage_sent_confirmation")
def send_foimessage_sent_confirmation(sender, message=None, **kwargs):
    messages = sender.get_messages()
    if len(messages) == 1:
        subject = _("Your Freedom of Information Request was sent")
        template = "foirequest/emails/confirm_foi_request_sent.txt"
    else:
        subject = _("Your Message was sent")
        template = "foirequest/emails/confirm_foi_message_sent.txt"
    send_mail(subject,
            render_to_string(template,
                {"request": sender, "message": message,
                    "site_name": settings.SITE_NAME}),
            settings.DEFAULT_FROM_EMAIL,
            [sender.user.email])


# Updating same_as foirequest count

@receiver(signals.post_save, sender=FoiRequest,
        dispatch_uid="foirequest_add_up_sameascount")
def foirequest_add_same_as_count(instance=None, created=False, **kwargs):
    if created and kwargs.get('raw', False):
        return
    from .tasks import count_same_foirequests
    if instance.same_as:
        count_same_foirequests.delay(instance.same_as.id)


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
        if (instance.belongs_to is not None and
                    instance.belongs_to.request_id is not None):
            trigger_index_update(FoiRequest, instance.belongs_to.request_id)
    except FoiMessage.DoesNotExist:
        pass


# Event creation

@receiver(FoiRequest.message_sent, dispatch_uid="create_event_message_sent")
def create_event_message_sent(sender, message, **kwargs):
    FoiEvent.objects.create_event("message_sent", sender, user=sender.user,
            public_body=message.recipient_public_body)


@receiver(FoiRequest.message_received,
        dispatch_uid="create_event_message_received")
def create_event_message_received(sender, **kwargs):
    FoiEvent.objects.create_event("message_received", sender,
            user=sender.user,
            public_body=sender.public_body)


@receiver(FoiRequest.status_changed,
        dispatch_uid="create_event_status_changed")
def create_event_status_changed(sender, **kwargs):
    status = kwargs['status']
    data = kwargs['data']
    if data.get('costs', 0) > 0:
        FoiEvent.objects.create_event("reported_costs", sender,
                user=sender.user,
                public_body=sender.public_body, amount=data['costs'])
    elif status == "refused" and data['refusal_reason']:
        FoiEvent.objects.create_event("request_refused", sender,
                user=sender.user,
                public_body=sender.public_body, reason=data['refusal_reason'])
    elif status == "partially_successful" and data['refusal_reason']:
        FoiEvent.objects.create_event("partially_successful", sender,
                user=sender.user,
                public_body=sender.public_body, reason=data['refusal_reason'])
    else:
        FoiEvent.objects.create_event("status_changed", sender, user=sender.user,
            public_body=sender.public_body,
            status=FoiRequest.get_readable_status(status))


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


@receiver(FoiRequest.add_postal_reply,
    dispatch_uid="create_event_add_postal_reply")
def create_event_add_postal_reply(sender, **kwargs):
    FoiEvent.objects.create_event("add_postal_reply", sender,
            user=sender.user)


@receiver(FoiRequest.escalated,
    dispatch_uid="create_event_escalated")
def create_event_escalated(sender, **kwargs):
    FoiEvent.objects.create_event("escalated", sender,
            user=sender.user, public_body=sender.law.mediator)


@receiver(signals.post_save, sender=FoiAttachment,
        dispatch_uid="foiattachment_convert_attachment")
def foiattachment_convert_attachment(instance=None, created=False, **kwargs):
    if kwargs.get('raw', False):
        return

    from .tasks import convert_attachment_task

    if (instance.filetype in FoiAttachment.CONVERTABLE_FILETYPES or
            instance.name.endswith(FoiAttachment.CONVERTABLE_FILETYPES)):
        if instance.converted_id is None:
            convert_attachment_task.delay(instance.id)
