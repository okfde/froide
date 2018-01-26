from django.apps import AppConfig
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _


class TeamConfig(AppConfig):
    name = 'froide.team'
    verbose_name = _('Teams')

    def ready(self):
        from froide.account.menu import menu_registry, MenuItem

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
