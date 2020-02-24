from froide.celery import app as celery_app

from .utils import (
    run_guidance, run_guidance_on_queryset, GuidanceApplicator,
    GuidanceResult, notify_users
)


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


@celery_app.task(name='froide.guide.tasks.add_action_to_queryset_task')
def add_action_to_queryset_task(action_id, message_ids):
    from froide.foirequest.models import FoiMessage
    from .models import Action

    try:
        action = Action.objects.get(id=action_id)
    except Action.DoesNotExist:
        return

    queryset = FoiMessage.objects.filter(id__in=message_ids)
    for message in queryset:
        applicator = GuidanceApplicator(message)
        guidance = applicator.apply_action(action)
        notify_users([(message, GuidanceResult(
            [guidance], applicator.created_count, 0
        ))])
