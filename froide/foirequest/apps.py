from django.apps import AppConfig
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class FoiRequestConfig(AppConfig):
    name = "froide.foirequest"
    verbose_name = _("FOI Request")

    def ready(self):
        from django_comments.signals import comment_will_be_posted

        from froide.account import (
            account_canceled,
            account_made_private,
            account_merged,
        )
        from froide.account.export import registry
        from froide.foirequest import signals  # noqa
        from froide.helper.search import search_registry
        from froide.team import team_changed

        from .utils import (
            cancel_user,
            export_user_data,
            make_account_private,
            merge_user,
        )

        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        account_made_private.connect(make_account_private)
        registry.register(export_user_data)
        search_registry.register(add_search)
        comment_will_be_posted.connect(signals.pre_comment_foimessage)
        team_changed.connect(keep_foiproject_teams_synced_with_requests)


def add_search(request):
    return {
        "title": _("Requests"),
        "name": "foirequest",
        "url": reverse("foirequest-list"),
    }


def keep_foiproject_teams_synced_with_requests(sender, team=None, **kwargs):
    from froide.foirequest.models import FoiProject, FoiRequest

    if isinstance(sender, FoiProject):
        FoiRequest.objects.filter(project=sender).update(team=team)
