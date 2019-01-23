from froide.celery import app as celery_app

from .utils import run_guidance, run_guidance_on_queryset


@celery_app.task(name='froide.guide.tasks.run_guidance_task')
def run_guidance_task(message_id):
    from froide.foirequest.models import FoiMessage

    try:
        message = FoiMessage.objects.get(id=message_id)
    except FoiMessage.DoesNotExist:
        return
    run_guidance(message)


@celery_app.task(name='froide.guide.tasks.run_guidance_on_queryset_task')
def run_guidance_on_queryset_task(message_ids, notify=False):
    from froide.foirequest.models import FoiMessage

    queryset = FoiMessage.objects.filter(id__in=message_ids)
    run_guidance_on_queryset(queryset, notify=notify)
