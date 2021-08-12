from django.utils import translation
from django.conf import settings

from froide.celery import app as celery_app
from froide.foirequest.models import FoiRequest

from .models import FoiRequestFollower
from .utils import run_batch_update


@celery_app.task
def update_followers(request_id, update_message, template=None):
    translation.activate(settings.LANGUAGE_CODE)
    try:
        foirequest = FoiRequest.objects.get(id=request_id)
    except FoiRequest.DoesNotExist:
        return

    followers = FoiRequestFollower.objects.filter(request=foirequest, confirmed=True)
    for follower in followers:
        FoiRequestFollower.objects.send_update(
            follower.user or follower.email,
            [
                {
                    "request": foirequest,
                    "unfollow_link": follower.get_unfollow_link(),
                    "events": [update_message],
                }
            ],
            batch=False,
        )


@celery_app.task
def batch_update():
    return run_batch_update()
