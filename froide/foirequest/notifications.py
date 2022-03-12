from collections import defaultdict
from datetime import datetime
from itertools import groupby
from typing import List, Optional

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from django_comments import get_model as get_comment_model

from froide.comments.notifications import make_event as make_comment_event
from froide.helper.date_utils import get_yesterday_datetime_range
from froide.helper.email_sending import mail_registry
from froide.helper.notifications import Notification

from .models import FoiEvent, FoiMessage
from .models.event import EVENT_DETAILS
from .utils import send_request_user_email

update_requester_email = mail_registry.register(
    "foirequest/emails/request_update", ("count", "user", "request_list")
)
classification_reminder_email = mail_registry.register(
    "foirequest/emails/classification_reminder",
    ("foirequest", "user", "action_url", "status_action_url"),
)

non_foi_email = mail_registry.register(
    "foirequest/emails/non_foi", ("foirequest", "user", "action_url")
)

Comment = get_comment_model()

# Interesting events
# message sent/received are already in instant updates
INTERESTING_EVENTS = set(EVENT_DETAILS.keys()) - set(
    [
        FoiEvent.EVENTS.MESSAGE_RECEIVED,
        FoiEvent.EVENTS.MESSAGE_SENT,
    ]
)

COMBINE_EVENTS = set(
    [
        FoiEvent.EVENTS.SET_SUMMARY,
        FoiEvent.EVENTS.ATTACHMENT_PUBLISHED,
        FoiEvent.EVENTS.STATUS_CHANGED,
    ]
)


def get_event_updates(start: datetime, end: datetime, **filter_kwargs):
    events = (
        FoiEvent.objects.filter(
            timestamp__gte=start, timestamp__lt=end, event_name__in=INTERESTING_EVENTS
        )
        .filter(**filter_kwargs)
        .select_related("request")
        .order_by("-timestamp")
    )
    already_seen = defaultdict(set)
    for event in events:
        if event.event_name in COMBINE_EVENTS:
            # Only report one of possibly multiple
            if event.event_name in already_seen[event.request_id]:
                continue
            already_seen[event.request_id].add(event.event_name)

        yield event.to_notification()


def get_comment_updates(start: datetime, end: datetime, **filter_kwargs):
    ct = ContentType.objects.get_for_model(FoiMessage)

    comments = Comment.objects.filter(
        content_type=ct, submit_date__gte=start, submit_date__lt=end
    ).filter(**filter_kwargs)

    for comment in comments:
        try:
            message = FoiMessage.objects.select_related("request").get(
                pk=comment.object_pk
            )
        except FoiMessage.DoesNotExist:
            continue

        yield Notification(
            section=_("Requests"),
            event_type="comment",
            object=message.request,
            object_label=message.request.title,
            timestamp=comment.submit_date,
            event=make_comment_event(comment),
            user_id=comment.user_id,
        )


def batch_update_requester(
    start: Optional[datetime] = None, end: Optional[datetime] = None
):
    if start is None or end is None:
        start, end = get_yesterday_datetime_range()

    yesterdays_comments = list(get_comment_updates(start, end))

    def key_func(n):
        return (n.object.user_id, n.object.id, n.timestamp)

    yesterdays_comments = sorted(yesterdays_comments, key=key_func)

    for user_id, group in groupby(yesterdays_comments, lambda n: n.object.user_id):
        if user_id is None:
            continue
        notifications = list(group)
        user = notifications[0].object.user
        send_update(notifications, user=user)


def send_update(notifications: List[Notification], user):
    translation.activate(user.language or settings.LANGUAGE_CODE)

    count = len(notifications)
    subject = ngettext_lazy(
        "Update on one of your request", "Update on %(count)s of your requests", count
    ) % {"count": count}

    # Add additional info to template context
    request_list = []
    grouped_notifications = groupby(notifications, lambda n: n.object.id)
    for _request_id, notifications in grouped_notifications:
        notifications = list(notifications)
        assert notifications[0].object.user_id == user.id
        foirequest = notifications[0].object

        # Don't add request if all comments are from requester
        if len([n for n in notifications if n.user_id != user.id]) == 0:
            continue

        request_list.append(
            {
                "request": foirequest,
                "events": [n.event.as_text() for n in notifications],
                "go_url": user.get_autologin_url(foirequest.get_absolute_short_url()),
            }
        )

    if not request_list:
        return

    update_requester_email.send(
        user=user,
        subject=subject,
        context={
            "user": user,
            "count": count,
            "request_list": request_list,
        },
    )


def send_classification_reminder(foirequest):
    if foirequest.user is None:
        return
    req_url = foirequest.user.get_autologin_url(foirequest.get_absolute_short_url())
    subject = _("Please classify the reply to your request")
    context = {
        "foirequest": foirequest,
        "user": foirequest.user,
        "action_url": req_url,
        "status_action_url": req_url + "#set-status",
    }
    send_request_user_email(
        classification_reminder_email,
        foirequest,
        subject=subject,
        context=context,
        priority=False,
    )


def send_non_foi_notification(foirequest):
    if foirequest.user is None:
        return
    req_url = foirequest.user.get_autologin_url(foirequest.get_absolute_short_url())
    subject = _("Your request is not suitable for our platform")
    context = {
        "foirequest": foirequest,
        "user": foirequest.user,
        "action_url": req_url,
    }
    send_request_user_email(
        non_foi_email, foirequest, subject=subject, context=context, priority=False
    )
