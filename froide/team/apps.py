import json

from django.apps import AppConfig
from django.urls import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _


class TeamConfig(AppConfig):
    name = 'froide.team'
    verbose_name = _('Teams')

    def ready(self):
        from froide.account.menu import menu_registry, MenuItem
        from froide.account import account_canceled, account_merged
        from froide.account.export import registry

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
        registry.register(export_user_data)

        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership
    from .models import TeamMembership

    move_ownership(
        TeamMembership, 'user', old_user, new_user,
        dupe=('user', 'team')
    )


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


def export_user_data(user):
    from .models import TeamMembership

    memberships = TeamMembership.objects.filter(
        user=user
    ).select_related('team')
    if not memberships:
        return
    yield ('teams.json', json.dumps([
        {
            'created': member.created.isoformat() if member.created else None,
            'updated': member.updated.isoformat() if member.created else None,
            'status': member.status,
            'email': member.email,
            'role': member.role,
            'team_name': member.team.name,
            'team_id': member.team_id,
        }
        for member in memberships]).encode('utf-8')
    )
