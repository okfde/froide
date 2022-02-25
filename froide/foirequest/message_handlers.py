from django.conf import settings
from django.utils import timezone

from froide.helper.utils import get_module_attr_from_dotted_path

from .foi_mail import send_foi_mail
from .models import DeliveryStatus


def get_message_handler_class(dotted):
    return get_module_attr_from_dotted_path(dotted)


def get_message_handler(message):
    kind = message.kind
    handler = settings.FROIDE_CONFIG["message_handlers"].get(kind)
    if handler is None:
        handler_klass = DefaultMessageHandler
    else:
        handler_klass = get_message_handler_class(handler)
    return handler_klass(message)


def send_message(message, **kwargs):
    handler = get_message_handler(message)
    handler.send(**kwargs)


def resend_message(message, **kwargs):
    handler = get_message_handler(message)
    handler.resend(**kwargs)


class MessageHandler(object):
    def __init__(self, message):
        self.message = message

    def send(self, **kwargs):
        message = self.message
        if message.is_response:
            return
        request = message.request

        ds = message.get_delivery_status()
        if ds is not None and ds.is_sent() and not kwargs.get("force"):
            raise ValueError("Delivery Status with sent exists!")

        if not request.is_blocked:
            self.run_send(**kwargs)

        request._messages = None

    def resend(self, **kwargs):
        message = self.message

        ds = message.get_delivery_status()
        if ds is not None and ds.is_sent() and not kwargs.get("force"):
            # If status is received, do not send
            return

        if ds:
            ds.retry_count += 1
            ds.save()

        message.sent = False
        message.save()

        self.send(**kwargs)

    def run_send(self, **kwargs):
        raise NotImplementedError


class DefaultMessageHandler(MessageHandler):
    def send(self, **kwargs):
        pass

    def resend(self, **kwargs):
        pass


class EmailMessageHandler(MessageHandler):
    def run_send(self, **kwargs):
        message = self.message
        request = message.request

        attachments = kwargs.get("attachments", [])

        extra_kwargs = {}
        # Use send_foi_mail here
        from_addr = request.get_sender_address()
        get_notified = (
            message.sender_user
            and message.sender_user.is_superuser
            and not request.public
        )
        if settings.FROIDE_CONFIG["read_receipt"] and get_notified:
            extra_kwargs["read_receipt"] = True
        if settings.FROIDE_CONFIG["delivery_receipt"] and get_notified:
            extra_kwargs["delivery_receipt"] = True
        if settings.FROIDE_CONFIG["dsn"] and get_notified:
            extra_kwargs["dsn"] = True

        message.timestamp = timezone.now()
        message.save()

        message.email_message_id = message.make_message_id()
        extra_kwargs["message_id"] = message.email_message_id
        froide_message_id = message.get_absolute_domain_short_url()
        extra_kwargs["froide_message_id"] = froide_message_id

        send_foi_mail(
            message.subject,
            message.plaintext,
            from_addr,
            [message.recipient_email.strip()],
            attachments=attachments,
            **extra_kwargs
        )

        message.sent = True
        message.save()

        DeliveryStatus.objects.update_or_create(
            message=message,
            defaults=dict(
                status=DeliveryStatus.Delivery.STATUS_SENDING,
                last_update=timezone.now(),
            ),
        )

        # Check delivery status in 2 minutes
        from .tasks import check_delivery_status

        check_delivery_status.apply_async((message.id,), {"count": 0}, countdown=2 * 60)
