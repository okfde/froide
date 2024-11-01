from datetime import timedelta

from django.apps import AppConfig
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class FoiRequestConfig(AppConfig):
    name = "froide.foirequest"
    verbose_name = _("FOI Request")

    def ready(self):
        from django_comments.signals import comment_will_be_posted

        from froide.account import (
            account_banned,
            account_canceled,
            account_confirmed,
            account_made_private,
            account_merged,
        )
        from froide.account.export import registry
        from froide.api import api_router
        from froide.foirequest import signals  # noqa
        from froide.foirequest.api_views.attachment import FoiAttachmentViewSet
        from froide.foirequest.api_views.message import FoiMessageViewSet
        from froide.foirequest.api_views.request import FoiRequestViewSet
        from froide.helper.search import search_registry
        from froide.team import team_changed

        from .utils import (
            cancel_user,
            depublish_requests,
            export_user_data,
            make_account_private,
            merge_user,
        )

        account_banned.connect(depublish_requests)
        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        account_made_private.connect(make_account_private)
        registry.register(export_user_data)
        search_registry.register(add_search)
        comment_will_be_posted.connect(signals.pre_comment_foimessage)
        team_changed.connect(keep_foiproject_teams_synced_with_requests)
        account_confirmed.connect(send_request_when_account_confirmed)

        api_router.register(r"request", FoiRequestViewSet, basename="request")
        api_router.register(r"message", FoiMessageViewSet, basename="message")
        api_router.register(r"attachment", FoiAttachmentViewSet, basename="attachment")


def add_search(request):
    return {
        "title": _("Requests"),
        "name": "foirequest",
        "url": reverse("foirequest-list"),
    }


def keep_foiproject_teams_synced_with_requests(sender, team=None, **kwargs):
    from .models import FoiProject, FoiRequest

    if isinstance(sender, FoiProject):
        FoiRequest.objects.filter(project=sender).update(team=team)


def send_request_when_account_confirmed(sender, request=None, **kwargs):
    from .models import FoiRequest
    from .services import ActivatePendingRequestService

    # request cannot be too old for confirmation
    # otherwise it has to be confirmed manually
    MAX_DAYS_OLD = 3
    not_older_than = timezone.now() - timedelta(days=MAX_DAYS_OLD)

    foirequest = FoiRequest.objects.filter(
        user=sender,
        status=FoiRequest.STATUS.AWAITING_USER_CONFIRMATION,
        created_at__gte=not_older_than,
    ).first()

    if not foirequest:
        return

    req_service = ActivatePendingRequestService({"foirequest": foirequest})
    foirequest = req_service.process(request=request)
    if foirequest:
        return {"request": str(foirequest.pk)}
