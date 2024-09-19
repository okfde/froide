import json

from django.apps import AppConfig
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class ProblemConfig(AppConfig):
    name = "froide.problem"
    verbose_name = _("Problems")

    def ready(self):
        from froide.account import account_merged
        from froide.account.export import registry
        from froide.account.menu import MenuItem, menu_registry
        from froide.api import api_router

        from . import signals  # noqa
        from .api_views import ProblemReportViewSet

        api_router.register(
            r"problemreport", ProblemReportViewSet, basename="problemreport"
        )

        registry.register(export_user_data)
        account_merged.connect(merge_user)

        def get_moderation_menu_item(request):
            from froide.foirequest.auth import is_foirequest_moderator

            if not is_foirequest_moderator(request):
                return None

            return MenuItem(
                section="after_settings",
                order=0,
                url=reverse("problem-moderation"),
                label=_("Moderation"),
            )

        menu_registry.register(get_moderation_menu_item)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from .models import ProblemReport

    ProblemReport.objects.filter(user=old_user).update(user=new_user)
    ProblemReport.objects.filter(moderator=old_user).update(moderator=new_user)


def export_user_data(user):
    from .models import ProblemReport

    problems = ProblemReport.objects.filter(user=user).select_related(
        "message", "message__request"
    )
    if not problems:
        return
    yield (
        "problem_reports.json",
        json.dumps(
            [
                {
                    "message": pb.message.get_absolute_domain_short_url(),
                    "timestamp": pb.timestamp.isoformat(),
                    "resolved": pb.resolved,
                    "kind": pb.kind,
                    "description": pb.description,
                    "resolution": pb.resolution,
                    "resolution_timestamp": (
                        pb.resolution_timestamp.isoformat()
                        if pb.resolution_timestamp
                        else None
                    ),
                }
                for pb in problems
            ]
        ).encode("utf-8"),
    )
