import logging

from django.conf import settings
from django.utils import translation

from celery.task import task
from celery.signals import task_failure
from haystack import site
from sentry.client.handlers import SentryHandler


# Hook up sentry to celery's logging
# Based on http://www.colinhowe.co.uk/2011/02/08/celery-and-sentry-recording-errors/

logger = logging.getLogger('task')
logger.addHandler(SentryHandler())
def process_failure_signal(exception, traceback, sender, task_id,
                            signal, args, kwargs, einfo, **kw):
    exc_info = (type(exception), exception, traceback)
    logger.error(
        'Celery job exception: %s(%s)' % (exception.__class__.__name__, exception),
        exc_info=exc_info,
        extra={
            'data': {
            'task_id': task_id,
            'sender': sender,
            'args': args,
            'kwargs': kwargs,
            }
        }
    )
task_failure.connect(process_failure_signal)

@task
def delayed_update(instance_pk, model):
    """ Only index stuff that is known to be public """
    translation.activate(settings.LANGUAGE_CODE)
    try:
        instance = model.published.get(pk=instance_pk)
    except (model.DoesNotExist, AttributeError):
        return
    site.update_object(instance)

@task
def delayed_remove(instance_pk, model):
    translation.activate(settings.LANGUAGE_CODE)
    # Fake an instance (real one is already gone from the DB)
    fake_instance = model()
    fake_instance.pk = instance_pk
    site.remove_object(fake_instance)

