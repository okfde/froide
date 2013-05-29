from datetime import datetime, timedelta

from celery.task import task

from django.utils.translation import ugettext as _
from django.utils import translation
from django.utils.dateformat import TimeFormat
from django.conf import settings
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from froide.foirequest.models import FoiRequest, FoiEvent, FoiMessage

from .models import FoiRequestFollower


@task
def update_followers(request_id, message):
    translation.activate(settings.LANGUAGE_CODE)
    try:
        foirequest = FoiRequest.objects.get(id=request_id)
        FoiRequest.objects.send_update(foirequest, message)
    except FoiRequest.DoesNotExist:
        pass


@task
def update_followers_postal_reply(request_id):
    try:
        foirequest = FoiRequest.objects.get(id=request_id)
    except FoiRequest.DoesNotExist:
        return
    FoiRequestFollower.objects.send_update(foirequest,
        _("The request '%(request)s' received a postal reply.") % {
            "request": foirequest.title})


@task
def batch_update():
    return _batch_update()


def _batch_update():
    event_black_list = ("message_received", "message_sent", 'set_concrete_law',)
    translation.activate(settings.LANGUAGE_CODE)
    requests = {}
    gte_date = timezone.now() - timedelta(days=1)
    updates = {}

    message_type = ContentType.objects.get_for_model(FoiMessage)
    for comment in Comment.objects.filter(content_type=message_type,
            submit_date__gte=gte_date):
        try:
            message = FoiMessage.objects.get(pk=comment.object_pk)
            if not message.request_id in requests:
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

    # send out update on comments to request users
    for req_id, request in requests.iteritems():
        if not updates[req_id]:
            continue
        if not any([x for x in updates[req_id] if x[2] != request.user_id]):
            continue

        sorted_events = sorted(updates[req_id], key=lambda x: x[0])
        event_string = "\n".join([x[1] for x in sorted_events])
        request.send_update(event_string)

    for event in FoiEvent.objects.filter(timestamp__gte=gte_date).select_related("request"):
        if event.event_name in event_black_list:
            continue
        if not event.request_id in requests:
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
    for req_id, request in requests.items():
        if not updates[req_id]:
            continue
        updates[req_id].sort(key=lambda x: x[0])
        event_string = "\n".join([x[1] for x in updates[req_id]])
        followers = FoiRequestFollower.objects.filter(request=request)
        for follower in followers:
            if not any([x for x in updates[req_id] if x[2] != follower.user_id]):
                continue
            follower.send_update(
                _("The following happend in the last 24 hours:\n%(events)s") % {
                    "events": event_string
                }
            )
