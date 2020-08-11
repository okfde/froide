from django.dispatch import receiver

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from froide.foirequest.models import FoiRequest
from froide.publicbody.models import PublicBody

from .models import (
    reported, claimed, unclaimed, escalated, resolved
)
from .utils import inform_managers
from .consumers import PRESENCE_ROOM
from .api_views import ProblemReportSerializer


@receiver(reported, dispatch_uid="report_problem_reported")
def broadcast_reported_report(sender, **kwargs):
    return broadcast_added_report(sender, **kwargs)


@receiver(claimed, dispatch_uid="report_problem_claimed")
def broadcast_claimed_report(sender, **kwargs):
    return broadcast_updated_report(sender, **kwargs)


@receiver(unclaimed, dispatch_uid="report_problem_unclaimed")
def broadcast_unclaimed_report(sender, **kwargs):
    return broadcast_updated_report(sender, **kwargs)


@receiver(resolved, dispatch_uid="report_problem_resolved")
def broadcast_resolved_report(sender, **kwargs):
    return broadcast_removed_report(sender, **kwargs)


@receiver(escalated, dispatch_uid="report_problem_escalated")
def broadcast_escalated_report(sender, **kwargs):
    inform_managers(sender)
    return broadcast_removed_report(sender, **kwargs)


def broadcast_updated_report(sender, **kwargs):
    data = ProblemReportSerializer(sender).data
    broadcast_moderation("report_updated", data)


def broadcast_added_report(sender, **kwargs):
    data = ProblemReportSerializer(sender).data
    broadcast_moderation("report_added", data)


def broadcast_removed_report(sender, **kwargs):
    broadcast_moderation("report_removed", {"id": sender.id})


def _get_pb_data(pb):
    return {
        "id": pb.id,
        "name": pb.name,
        "confirmed": pb.confirmed
    }


@receiver(PublicBody.proposal_added,
          dispatch_uid="pb_proposal_added_broadcast")
def broadcast_pb_proposal(sender, **kwargs):
    broadcast_moderation(
        "publicbody_added", _get_pb_data(sender), key='publicbody'
    )


@receiver(PublicBody.proposal_accepted,
          dispatch_uid="pb_proposal_accepted_broadcast")
def broadcast_pb_proposal_accepted(sender, **kwargs):
    broadcast_moderation(
        "publicbody_removed", _get_pb_data(sender), key='publicbody')


@receiver(PublicBody.proposal_rejected,
          dispatch_uid="pb_proposal_rejected_broadcast")
def broadcast_pb_proposal_rejected(sender, **kwargs):
    broadcast_moderation(
        "publicbody_removed", _get_pb_data(sender), key='publicbody')


@receiver(PublicBody.change_proposal_added,
          dispatch_uid="pb_change_proposal_added_broadcast")
def broadcast_pb_change_proposal(sender, **kwargs):
    broadcast_moderation(
        "publicbody_added", _get_pb_data(sender), key='publicbody'
    )


@receiver(PublicBody.change_proposal_accepted,
          dispatch_uid="pb_change_proposal_accepted_broadcast")
def broadcast_pb_change_proposal_accepted(sender, **kwargs):
    broadcast_moderation(
        "publicbody_removed", _get_pb_data(sender), key='publicbody'
    )


def _get_unclassified_data(fr):
    return {
        "id": fr.id,
        "title": fr.title,
    }


@receiver(FoiRequest.status_changed,
        dispatch_uid="unclassified_status_changed")
def broadcast_unclassified_changed(sender, **kwargs):
    prev = kwargs.get('previous_status')
    if prev != FoiRequest.STATUS.AWAITING_CLASSIFICATION:
        return
    if not sender.available_for_moderator_action():
        return
    broadcast_moderation(
        "unclassified_removed", _get_unclassified_data(sender),
        key='unclassified'
    )


def broadcast_moderation(broadcast, data, key="report"):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        PRESENCE_ROOM, {
            "type": broadcast,
            key: data
        }
    )
