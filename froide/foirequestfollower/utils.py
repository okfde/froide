from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import formats, timezone, translation
from django.utils.translation import gettext as _

from django_comments import get_model

from froide.foirequest.models import FoiEvent, FoiMessage
from froide.foirequest.models.event import EVENT_DETAILS
from froide.foirequest.notifications import send_update

from .forms import FollowRequestForm
from .models import REFERENCE_PREFIX, FoiRequestFollower

Comment = get_model()

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


def get_context(foirequest, request, **kwargs):
    form = FollowRequestForm(foirequest=foirequest, request=request)
    following = False
    user = request.user
    if user.is_authenticated:
        following = FoiRequestFollower.objects.request_followed_by(
            foirequest, user=user
        )
    context = {
        "form": form,
        "object": foirequest,
        "following": following,
        "request": request,
        "can_follow": foirequest.user != user,
    }
    context.update(kwargs)
    return context


def add_comment_updates(updates, since):
    message_type = ContentType.objects.get_for_model(FoiMessage)

    comments = Comment.objects.filter(content_type=message_type, submit_date__gte=since)

    for comment in comments:
        try:
            message = FoiMessage.objects.select_related("request").get(
                pk=comment.object_pk
            )
        except FoiMessage.DoesNotExist:
            continue

        time = formats.date_format(
            timezone.localtime(comment.submit_date), "TIME_FORMAT"
        )
        updates[message.request].append(
            (
                comment.submit_date,
                _("%(time)s: New comment by %(name)s")
                % {"time": time, "name": comment.user_name},
                comment.user_id,
            )
        )


def add_event_updates(updates, since):
    events = (
        FoiEvent.objects.filter(timestamp__gte=since, event_name__in=INTERESTING_EVENTS)
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

        time = formats.date_format(timezone.localtime(event.timestamp), "TIME_FORMAT")
        updates[event.request].append(
            (
                event.timestamp,
                _("%(time)s: %(text)s") % {"time": time, "text": event.as_text()},
                event.user_id,
            )
        )


def send_requester_update(updates):
    requester_updates = defaultdict(list)
    # send out update on comments to request users
    for request, update_list in updates.items():
        if not update_list:
            continue
        if not any([x for x in update_list if x[2] != request.user_id]):
            continue

        sorted_events = sorted(update_list, key=lambda x: x[0])

        requester_updates[request.user].append(
            {"request": request, "events": [x[1] for x in sorted_events]}
        )

    for user, request_list in requester_updates.items():
        send_update(request_list, user=user)


def get_follower_updates(updates):
    follower_updates = defaultdict(list)
    for request, update_list in updates.items():
        if not update_list:
            continue
        if not request.is_public():
            continue
        update_list.sort(key=lambda x: x[0])
        followers = FoiRequestFollower.objects.filter(
            request=request, confirmed=True
        ).select_related("user")
        for follower in followers:
            if not any([x for x in update_list if x[2] != follower.user_id]):
                continue
            ident = follower.user or follower.email
            follower_updates[ident].append(
                {
                    "request": request,
                    "unfollow_link": follower.get_unfollow_link(),
                    "events": [x[1] for x in update_list],
                }
            )

    return follower_updates


def run_batch_update(update_requester=True, update_follower=True, since=None):
    if since is None:
        since = timezone.now() - timedelta(days=1)

    translation.activate(settings.LANGUAGE_CODE)
    updates = defaultdict(list)

    add_comment_updates(updates, since)

    if update_requester:
        send_requester_update(updates)

    if update_follower:
        # update followers
        add_event_updates(updates, since)

        follower_updates = get_follower_updates(updates)

        # Send out update on comments and event to followers
        for follower_ident, update_list in follower_updates.items():
            FoiRequestFollower.objects.send_update(
                follower_ident, update_list, batch=True
            )


def handle_bounce(sender, bounce, should_deactivate=False, **kwargs):
    if not should_deactivate:
        return

    FoiRequestFollower.objects.filter(email=bounce.email).delete()


def handle_unsubscribe(sender, email, reference, **kwargs):
    if not reference.startswith(REFERENCE_PREFIX):
        # not for us
        return
    try:
        follow_id = int(reference.split(REFERENCE_PREFIX, 1)[1])
    except ValueError:
        return
    try:
        follow = FoiRequestFollower.objects.get(
            id=follow_id,
            email=email,
        )
    except FoiRequestFollower.DoesNotExist:
        return
    follow.delete()
