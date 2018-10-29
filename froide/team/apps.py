from django.apps import AppConfig
from django.urls import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _


class TeamConfig(AppConfig):
    name = 'froide.team'
    verbose_name = _('Teams')

    def ready(self):
        from froide.account.menu import menu_registry, MenuItem
        from froide.account import account_canceled

        from .services import can_use_team

        def get_account_menu_item(request):
            if not can_use_team(request.user):
                return None

            return MenuItem(
                section='before_settings', order=0,
                url=reverse('team-list'),
                label=_('Your teams')
            )

        menu_registry.register(get_account_menu_item)

        account_canceled.connect(cancel_user)


def cancel_user(sender, user=None, **kwargs):
    from .models import Team

    if user is None:
        return

    # FIXME: teams may become owner-less
    user.teammembership_set.all().delete()

    # Remove teams with no members
    Team.objects.all().annotate(
        num_members=models.Count('members', distinct=True)
    ).filter(num_members=0).delete()
