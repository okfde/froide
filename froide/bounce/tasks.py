from django.conf import settings

from froide.celery import app as celery_app

from .utils import check_bounce_mails, check_unsubscribe_mails


HANDLE_BOUNCES = settings.FROIDE_CONFIG['bounce_enabled']
HANDLE_UNSUBSCRIBE = settings.FROIDE_CONFIG['unsubscribe_enabled']


@celery_app.task(name='froide.bounce.tasks.check_bounces', expires=60 * 60)
def check_bounces():
    if not HANDLE_BOUNCES:
        return
    check_bounce_mails()


@celery_app.task(name='froide.bounce.tasks.check_unsubscribe', expires=60 * 60)
def check_unsubscribe():
    if not HANDLE_UNSUBSCRIBE:
        return
    check_unsubscribe_mails()
