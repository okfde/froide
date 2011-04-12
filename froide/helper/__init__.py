from celery.task import Task
from celery.registry import tasks
from django.conf import settings
from django.core.management.base import NoArgsCommand

from mailer.engine import send_all
from mailer.models import Message

PAUSE_SEND = getattr(settings, "MAILER_PAUSE_SEND", False)


class RetryDeferred(Task):
    name = 'mailer.retry_deferred'
    
    def run(self, **kwargs):
        logger = self.get_logger(**kwargs)
        count = Message.objects.retry_deferred()
        logger.info("%s message(s) retried" % count)


class SendMail(Task):
    name = 'mailer.send_mail'
    
    def run(self, **kwargs):
        logger = self.get_logger(**kwargs)
        if not PAUSE_SEND:
            send_all()
        else:
            logger.info("sending is paused, quitting.")

            
tasks.register(RetryDeferred)
tasks.register(SendMail)

