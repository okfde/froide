from django.conf import settings

from froide.celery import app as celery_app

from .utils import check_bounce_mails


HANDLE_BOUNCES = settings.FROIDE_CONFIG['bounce_enabled']


@celery_app.task(name='froide.bounce.tasks.check_bounces', expires=60 * 60)
def check_bounces():
    if not HANDLE_BOUNCES:
        return
    check_bounce_mails()
