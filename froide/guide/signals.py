from functools import partial

from django.db import transaction

from .tasks import run_guidance_task


def start_guidance_task(sender, message=None, **kwargs):
    if not message or not message.is_response:
        return
    transaction.on_commit(partial(run_guidance_task.delay, message.id))
