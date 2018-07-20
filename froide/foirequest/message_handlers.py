import importlib

from django.conf import settings

from froide.helper.email_utils import make_address

from .foi_mail import send_foi_mail
from .models import FoiRequest


def get_message_handler_class(dotted):
    module, klass = dotted.rsplit('.', 1)
    module = importlib.import_module(module)
    return getattr(module, klass)


def get_message_handler(message):
    kind = message.kind
    handler = settings.FROIDE_CONFIG['message_handlers'].get(kind)
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
        if ds is not None and ds.is_sent():
            raise ValueError('Delivery Status with sent exists!')

        if not request.is_blocked:
            self.run_send(**kwargs)

        request._messages = None
        if kwargs.get('notify', True):
            FoiRequest.message_sent.send(
                sender=request, message=message
            )

    def resend(self, **kwargs):
        message = self.message

        ds = message.get_delivery_status()
        if ds is not None and ds.is_sent():
            # If status is received, do not send
            return

        if ds:
            ds.retry_count += 1
            ds.save()

        message.sent = False
        message.save()

        kwargs['notify'] = False
        self.send(**kwargs)

    def run_send(self, **kwargs):
        raise NotImplementedError


class DefaultMessageHandler(MessageHandler):
    def send(self, **kwargs):
        pass

    def resend(self, **kwargs):
        pass


class EmailMessageHandler(MessageHandler):
    def run_send(self, notify=True, **kwargs):
        message = self.message
        request = message.request

        attachments = kwargs.get('attachments', [])

        extra_kwargs = {}
        if settings.FROIDE_CONFIG['dryrun']:
            recp = message.recipient_email.replace("@", "+")
            message.recipient_email = "%s@%s" % (
                recp,
                settings.FROIDE_CONFIG['dryrun_domain']
            )
        # Use send_foi_mail here
        from_addr = make_address(
            request.secret_address,
            request.user.get_full_name()
        )
        get_notified = (message.sender_user.is_superuser and
                        not request.public)
        if settings.FROIDE_CONFIG['read_receipt'] and get_notified:
            extra_kwargs['read_receipt'] = True
        if settings.FROIDE_CONFIG['delivery_receipt'] and get_notified:
            extra_kwargs['delivery_receipt'] = True
        if settings.FROIDE_CONFIG['dsn'] and get_notified:
            extra_kwargs['dsn'] = True

        message.save()
        message_id = message.get_absolute_domain_short_url()
        extra_kwargs['froide_message_id'] = message_id

        attachments.extend([
            (a.name, a.get_bytes(), a.filetype) for a in message.attachments
        ])

        send_foi_mail(
            message.subject, message.plaintext, from_addr,
            [message.recipient_email.strip()],
            attachments=attachments,
            **extra_kwargs
        )
        message.email_message_id = ''
        message.sent = True
        message.save()

        # Check delivery status in 2 minutes
        from .tasks import check_delivery_status
        check_delivery_status.apply_async((message.id,), {'count': 0},
                                            countdown=2 * 60)
