from django.dispatch import receiver

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

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
    broadcast_report("report_updated", data)


def broadcast_added_report(sender, **kwargs):
    data = ProblemReportSerializer(sender).data
    broadcast_report("report_added", data)


def broadcast_removed_report(sender, **kwargs):
    broadcast_report("report_removed", {"id": sender.id})


def broadcast_report(broadcast, data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        PRESENCE_ROOM, {
            "type": broadcast,
            "report": data
        }
    )
