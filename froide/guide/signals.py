from .tasks import run_guidance_task


def start_guidance_task(sender, message=None, **kwargs):
    if not message or not message.is_response:
        return
    run_guidance_task.delay(message.id)
