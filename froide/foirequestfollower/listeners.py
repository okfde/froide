from django.dispatch import receiver

from froide.foirequest.models import FoiRequest

from .models import FoiRequestFollower


@receiver(FoiRequest.message_received, dispatch_uid="notify_followers_message_received")
def notify_followers_message_received(sender, message=None, **kwargs):
    from froide.follow.tasks import update_followers

    countdown = 0
    if message and message.is_postal:
        # Add delay so attachments can be uploaded/processed
        countdown = 10 * 60  # 10 minutes

    update_followers.apply_async(
        args=[
            "message_received",
            FoiRequestFollower._meta.label_lower,
            sender.pk,
        ],
        countdown=countdown,
    )


@receiver(FoiRequest.message_sent, dispatch_uid="notify_followers_send_foimessage")
def notify_followers_send_foimessage(sender, message=None, **kwargs):
    from froide.follow.tasks import update_followers

    countdown = 0
    if message and message.is_postal:
        # Add delay so attachments can be uploaded/processed
        countdown = 10 * 60  # 10 minutes

    update_followers.apply_async(
        args=[
            "message_sent",
            FoiRequestFollower._meta.label_lower,
            sender.pk,
        ],
        countdown=countdown,
    )
