import logging

from froide.celery import app as celery_app

from .configuration import follow_registry
from .notifications import run_batch_update, send_notification


@celery_app.task
def update_followers(event_type: str, model_name: str, content_object_id: int):
    try:
        configuration = follow_registry.get_by_model_name(model_name)
    except LookupError:
        return

    content_model = configuration.content_model

    try:
        content_object = content_model.objects.get(id=content_object_id)
    except content_model.DoesNotExist:
        return
    try:
        notification = configuration.make_notification(event_type, content_object)
    except LookupError:
        logging.exception("Could not make message for event_type %s", event_type)
        return
    send_notification(notification)


@celery_app.task
def batch_update():
    return run_batch_update()


@celery_app.task
def cleanup_unconfirmed_email_follows():
    for model in follow_registry.get_models():
        model.objects.cleanup_unconfirmed_email_follows()
