from .tasks import run_guidance_task


def start_guidance_task(sender, message=None, **kwargs):
    run_guidance_task.delay(message.id)
