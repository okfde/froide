from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from froide.foirequest.models import FoiRequest


@receiver(FoiRequest.message_received,
    dispatch_uid="notify_followers_message_received")
def notify_followers_message_received(sender, message=None, **kwargs):
    from .tasks import update_followers

    countdown = 0
    if message and message.is_postal:
        # Add delay so attachments can be uploaded/processed
        countdown = 10 * 60  # 10 minutes

    update_followers.apply_async(
        args=[sender.pk, _("The request '%(request)s' received a reply.") % {
            "request": sender.title}],
        kwargs={'template': 'foirequestfollower/instant_update_follower.txt'},
        countdown=countdown
    )


@receiver(FoiRequest.message_sent,
        dispatch_uid="notify_followers_send_foimessage")
def notify_followers_send_foimessage(sender, message=None, **kwargs):
    from .tasks import update_followers

    countdown = 0
    if message and message.is_postal:
        # Add delay so attachments can be uploaded/processed
        countdown = 10 * 60  # 10 minutes

    update_followers.apply_async(
        args=[sender.pk, _("A message was sent in the request '%(request)s'.") % {
            "request": sender.title}],
        kwargs={'template': 'foirequestfollower/instant_update_follower.txt'},
        countdown=countdown
    )
