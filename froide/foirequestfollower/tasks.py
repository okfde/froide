from datetime import timedelta
from collections import defaultdict

from django.utils.six import iteritems
from django.utils.translation import ugettext as _
from django.utils import translation
from django.utils.dateformat import TimeFormat
from django.conf import settings
from django_comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from froide.celery import app as celery_app
from froide.foirequest.models import FoiRequest, FoiEvent, FoiMessage

from .models import FoiRequestFollower


@celery_app.task
def update_followers(request_id, message, template=None):
    translation.activate(settings.LANGUAGE_CODE)
    try:
        foirequest = FoiRequest.objects.get(id=request_id)
        FoiRequestFollower.objects.send_update(foirequest, message,
                                               template=template)
    except FoiRequest.DoesNotExist:
        pass


@celery_app.task
def batch_update():
    return _batch_update()


def _batch_update(update_requester=True, update_follower=True):
    event_black_list = ("message_received", "message_sent", 'set_concrete_law',)
    translation.activate(settings.LANGUAGE_CODE)
    requests = {}
    users = {}
    gte_date = timezone.now() - timedelta(days=1)
    updates = {}

    message_type = ContentType.objects.get_for_model(FoiMessage)
    for comment in Comment.objects.filter(content_type=message_type,
            submit_date__gte=gte_date):
        try:
            message = FoiMessage.objects.get(pk=comment.object_pk)
            if message.request_id not in requests:
                requests[message.request_id] = message.request
            updates.setdefault(message.request_id, [])
            tf = TimeFormat(comment.submit_date)
            updates[message.request_id].append(
                (
                    comment.submit_date,
                    _("%(time)s: New comment by %(name)s") % {
                        "time": tf.format(_(settings.TIME_FORMAT)),
                        "name": comment.name
                    },
                    comment.user_id
                )
            )
        except FoiMessage.DoesNotExist:
            pass

    if update_requester:
        requester_updates = defaultdict(dict)
        # send out update on comments to request users
        for req_id, request in iteritems(requests):
            if not request.user.is_active:
                continue
            if not request.user.email:
                continue
            if not updates[req_id]:
                continue
            if not any([x for x in updates[req_id] if x[2] != request.user_id]):
                continue

            sorted_events = sorted(updates[req_id], key=lambda x: x[0])

            requester_updates[request.user][request] = {
                'events': [x[1] for x in sorted_events]
            }

        for user, request_dict in iteritems(requester_updates):
            FoiRequest.send_update(request_dict, user=user)

    if update_follower:
        # update followers

        for event in FoiEvent.objects.filter(timestamp__gte=gte_date).select_related("request"):
            if event.event_name in event_black_list:
                continue
            if event.request_id not in requests:
                requests[event.request_id] = event.request
            updates.setdefault(event.request_id, [])
            tf = TimeFormat(event.timestamp)
            updates[event.request_id].append(
                (
                    event.timestamp,
                    _("%(time)s: %(text)s") % {
                        "time": tf.format(_("TIME_FORMAT")),
                        "text": event.as_text()
                    },
                    event.user_id
                )
            )

        # Send out update on comments and event to followers
        follower_updates = defaultdict(dict)
        for req_id, request in iteritems(requests):
            if not updates[req_id]:
                continue
            updates[req_id].sort(key=lambda x: x[0])
            followers = FoiRequestFollower.objects.filter(
                    request=request).select_related('user')
            for follower in followers:
                if follower.user is None and not follower.confirmed:
                    continue
                if follower.user and (
                        not follower.user.is_active or not follower.user.email):
                    continue
                if not request.is_visible():
                    continue
                if not any([x for x in updates[req_id] if x[2] != follower.user_id]):
                    continue
                users[follower.user_id] = follower.user
                ident = follower.user_id or follower.email
                follower_updates[ident][request] = {
                    'unfollow_link': follower.get_unfollow_link(),
                    'events': [x[1] for x in updates[req_id]]
                }

        for user_id, req_event_dict in iteritems(follower_updates):
            user = users.get(user_id)
            email = None
            if user is None:
                email = user_id
            FoiRequestFollower.send_update(req_event_dict, user=user, email=email)
