import itertools
from datetime import datetime

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from froide.foirequest.auth import can_read_foirequest, get_read_foirequest_queryset
from froide.foirequest.models import FoiRequest
from froide.foirequest.notifications import get_comment_updates, get_event_updates
from froide.follow.configuration import FollowConfiguration
from froide.helper.notifications import Notification, TemplatedEvent

from .models import FoiRequestFollower


class FoiRequestFollowConfiguration(FollowConfiguration):
    model = FoiRequestFollower
    title: str = _("Requests")
    slug: str = "request"
    follow_message: str = _("You are now following this request.")
    unfollow_message: str = _("You are not following this request anymore.")
    confirm_email_message: str = _(
        "Check your emails and click the confirmation link in order to follow this request."
    )
    action_labels = {
        "follow": _("Follow request"),
        "follow_q": _("Follow request?"),
        "unfollow": _("Unfollow request"),
        "following": _("Following request"),
        "follow_description": _(
            "You will get notifications via email when something new happens with this request. You can unsubscribe anytime."
        ),
    }

    def get_content_object_queryset(self, request):
        qs = get_read_foirequest_queryset(request)
        if request.user.is_authenticated:
            qs = qs.exclude(user=request.user)
        return qs

    def can_follow(self, content_object, user, request=None):
        if request and not can_read_foirequest(content_object, request):
            return False

        if user.is_authenticated:
            return content_object.user != user

        return super().can_follow(content_object, user)

    def get_batch_updates(self, start: datetime, end: datetime):
        return itertools.chain(
            get_comment_updates(start, end), get_event_updates(start, end)
        )

    def get_confirm_follow_message(self, content_object):
        return _(
            "please confirm that you want to follow the request “{title}” on {site_name} by clicking this link:"
        ).format(title=content_object.title, site_name=settings.SITE_NAME)

    def merge_user(self, old_user, new_user):
        # Don't allow self follows on merge
        self.model.objects.filter(user=new_user, content_object__user=new_user).delete()

    def email_changed(self, user):
        # Move all confirmed email subscriptions of new email
        # to user except own requests
        self.model.objects.filter(email=user.email, confirmed=True).exclude(
            content_object__user=user
        ).update(email="", user=user)
        # Delete (attempted) email follows with the user's
        # email address to the users requests
        self.model.objects.filter(email=user.email, content_object__user=user).delete()

    def make_notification(
        self, event_type: str, content_object: FoiRequest
    ) -> Notification:
        if event_type == "message_received":
            event = TemplatedEvent(
                _("The request “{title}” received a reply."), title=content_object.title
            )
        elif event_type == "message_sent":
            event = TemplatedEvent(
                _("A message was sent in the request “{title}”."),
                title=content_object.title,
            )
        else:
            raise LookupError("Unknown event type")

        return Notification(
            section=_("Requests"),
            event_type=event_type,
            object=content_object,
            object_label=content_object.title,
            timestamp=content_object.last_message,
            event=event,
            user_id=None,
        )
