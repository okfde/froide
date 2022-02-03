import json

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FoiRequestFollowerConfig(AppConfig):
    name = "froide.foirequestfollower"
    verbose_name = _("FOI Request Follower")

    def ready(self):
        import froide.foirequestfollower.listeners  # noqa
        from froide.account import (
            account_canceled,
            account_email_changed,
            account_merged,
        )
        from froide.account.export import registry
        from froide.bounce.signals import email_bounced, email_unsubscribed
        from froide.foirequest.models import FoiRequest

        from .utils import handle_bounce, handle_unsubscribe

        account_canceled.connect(cancel_user)
        account_email_changed.connect(email_changed)
        account_merged.connect(merge_user)
        registry.register(export_user_data)

        email_bounced.connect(handle_bounce)
        email_unsubscribed.connect(handle_unsubscribe)
        FoiRequest.made_private.connect(remove_followers)


def cancel_user(sender, user=None, **kwargs):
    from .models import FoiRequestFollower

    if user is None:
        return
    FoiRequestFollower.objects.filter(user=user).delete()


def email_changed(sender=None, old_email=None, **kwargs):
    from .models import FoiRequestFollower

    # Move all confirmed email subscriptions of new email
    # to user except own requests
    FoiRequestFollower.objects.filter(email=sender.email, confirmed=True).exclude(
        request__user=sender
    ).update(email="", user=sender)
    # Delete (attempted) email follows with the user's
    # email address to the users requests
    FoiRequestFollower.objects.filter(email=sender.email, request__user=sender).delete()


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership

    from .models import FoiRequestFollower

    move_ownership(
        FoiRequestFollower,
        "user_id",
        old_user.id,
        new_user.id,
        dupe=(
            "user_id",
            "request_id",
        ),
    )
    # Don't follow your own requests
    FoiRequestFollower.objects.filter(user=new_user, request__user=new_user).delete()


def export_user_data(user):
    from froide.foirequest.models.request import get_absolute_domain_short_url

    from .models import FoiRequestFollower

    following = FoiRequestFollower.objects.filter(user=user)
    if not following:
        return
    yield (
        "followed_requests.json",
        json.dumps(
            [
                {
                    "timestamp": frf.timestamp.isoformat(),
                    "url": get_absolute_domain_short_url(frf.request_id),
                }
                for frf in following
            ]
        ).encode("utf-8"),
    )


def remove_followers(sender=None, **kwargs):
    from .models import FoiRequestFollower

    FoiRequestFollower.objects.filter(request=sender).delete()
