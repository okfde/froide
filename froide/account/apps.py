from typing import Optional

from django.apps import AppConfig
from django.http import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from froide.account.menu import MenuItem

from .menu import menu_registry


class AccountConfig(AppConfig):
    name = "froide.account"
    verbose_name = _("Account")

    def ready(self):
        from froide.bounce.signals import user_email_bounced

        user_email_bounced.connect(deactivate_user_after_bounce)

        menu_registry.register(get_settings_menu_item)
        menu_registry.register(get_request_menu_item)
        menu_registry.register(get_profile_menu_item)


def deactivate_user_after_bounce(sender, bounce, should_deactivate=False, **kwargs):
    if not should_deactivate:
        return
    if not bounce.user:
        return
    bounce.user.deactivate()


def get_request_menu_item(request: HttpRequest) -> MenuItem:
    return MenuItem(
        section="before_request",
        order=999,
        url=reverse("account-show"),
        label=_("My requests"),
    )


def get_profile_menu_item(request: HttpRequest) -> Optional[MenuItem]:
    if not request.user.is_authenticated:
        return None
    if request.user.private or not request.user.username:
        return None
    return MenuItem(
        section="before_settings",
        order=0,
        url=reverse("account-profile", kwargs={"slug": request.user.username}),
        label=_("My public profile"),
    )


def get_settings_menu_item(request: HttpRequest) -> MenuItem:
    return MenuItem(
        section="after_settings",
        order=-1,
        url=reverse("account-settings"),
        label=_("Settings"),
    )
