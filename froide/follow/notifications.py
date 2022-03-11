import itertools
from collections import defaultdict
from typing import Dict, List

from django.conf import settings
from django.utils import translation

from froide.foirequest.notifications import get_comment_updates, get_event_updates
from froide.helper.date_utils import get_yesterday_datetime_range
from froide.helper.email_sending import mail_registry
from froide.helper.notifications import Notification

from .configuration import follow_registry
from .models import FollowerIdent, FollowerItem

update_follower_email = mail_registry.register(
    "follow/emails/update_follower", ("count", "user", "update_list")
)

batch_update_follower_email = mail_registry.register(
    "follow/emails/batch_update_follower", ("count", "user", "update_list")
)


def get_follower_updates(
    notifications: List[Notification],
) -> Dict[FollowerIdent, FollowerItem]:
    follower_updates = defaultdict(list)

    def key_func(n):
        return (n.section, n.object.id, n.timestamp)

    notifications = sorted(notifications, key=key_func)

    for (section, _obj_id), update_list in itertools.groupby(
        notifications, lambda n: (n.section, n.object.id)
    ):
        update_list = list(update_list)
        if not update_list:
            continue

        content_object = update_list[0].object

        configurations = follow_registry.list_by_content_model(content_object.__class__)
        for configuration in configurations:
            if not configuration.wants_update(update_list):
                continue

            follower_model = configuration.model

            followers = follower_model.objects.filter(
                content_object=content_object, confirmed=True
            ).select_related("user")
            for follower in followers:
                if not any(
                    [
                        n
                        for n in update_list
                        if n.user_id is None or n.user_id != follower.user_id
                    ]
                ):
                    continue
                ident = follower.get_ident()

                if follower.user and follower.user.language:
                    lang = follower.user.language
                else:
                    lang = settings.LANGUAGE_CODE

                with translation.override(lang):
                    follower_updates[ident].append(
                        FollowerItem(
                            section=section,
                            content_object=content_object,
                            object_label=update_list[0].object_label,
                            unfollow_link=follower.get_unfollow_link(),
                            events=[n.event.as_text() for n in update_list],
                        )
                    )

    return follower_updates


def send_notification(notification: Notification):
    follower_updates = get_follower_updates([notification])

    # Send out update on comments and event to followers
    for follower_ident, update_list in follower_updates.items():
        send_update(follower_ident, update_list, batch=False)


def run_batch_update(start=None, end=None):
    if start is None and end is None:
        start, end = get_yesterday_datetime_range()

    notifications = list(
        itertools.chain(get_comment_updates(start, end), get_event_updates(start, end))
    )

    follower_updates = get_follower_updates(notifications)

    # Send out update on comments and event to followers
    for follower_ident, update_list in follower_updates.items():
        send_update(follower_ident, update_list, batch=True)


def send_update(user_or_email: FollowerIdent, update_list, batch=False):
    if not user_or_email:
        return
    user, email = None, None
    if isinstance(user_or_email, str):
        email = user_or_email
    else:
        user = user_or_email

    count = len(update_list)
    context = {
        "user": user,
        "email": email,
        "count": count,
        "update_list": update_list,
    }
    # if count == 1:
    #     configurations = follow_registry.list_by_content_model(
    #         update_list[0].content_object.__class__
    #     )
    #     follower = configuration.model.objects.get(
    #         content_object=update_list[0].content_object,
    #         email=email or "",
    #         user=user,
    #         confirmed=True,
    #     )
    #     context.update(follower.get_context())
    if batch:
        mail_intent = batch_update_follower_email
    else:
        mail_intent = update_follower_email

    mail_intent.send(user=user, email=email, context=context)
