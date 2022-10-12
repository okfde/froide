import json

from django.apps import AppConfig
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class OrganizationConfig(AppConfig):
    name = "froide.organization"
    verbose_name = _("Organization")

    def ready(self):
        from froide.account import (
            account_activated,
            account_canceled,
            account_email_changed,
            account_merged,
        )
        from froide.account.export import registry
        from froide.account.menu import MenuItem, menu_registry

        def get_organizations_menu_item(request):
            return MenuItem(
                section="before_settings",
                order=0,
                url=reverse("organization-list_own"),
                label=_("My organizations"),
            )

        menu_registry.register(get_organizations_menu_item)

        registry.register(export_user_data)

        account_activated.connect(connect_organization)
        account_email_changed.connect(disconnect_organization)
        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)


def connect_organization(sender, user, **kwargs):
    from .models import Organization

    org = Organization.objects.get_by_email(user.email)
    if org is None:
        return
    Organization.objects.add_user(user)


def disconnect_organization(sender, old_email=None, **kwargs):
    from .models import Organization, OrganizationMembership

    if old_email is None:
        return
    org = Organization.objects.get_by_email(old_email)
    OrganizationMembership.objects.filter(organization=org, user=sender).delete()


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership

    from .models import OrganizationMembership

    move_ownership(
        OrganizationMembership,
        "user",
        old_user,
        new_user,
        dupe=("user", "organization"),
    )


def cancel_user(sender, user=None, **kwargs):
    from .models import OrganizationMembership

    if user is None:
        return

    OrganizationMembership.objects.filter(user=user).delete()


def export_user_data(user):
    from .models import OrganizationMembership

    memberships = OrganizationMembership.objects.filter(user=user).select_related(
        "organization"
    )
    if not memberships:
        return
    yield (
        "organizations.json",
        json.dumps(
            [
                {
                    "created": member.created.isoformat() if member.created else None,
                    "updated": member.updated.isoformat() if member.created else None,
                    "status": member.status,
                    "email": member.email,
                    "role": member.role,
                    "team_name": member.organization.name,
                    "team_id": member.organization_id,
                }
                for member in memberships
            ]
        ).encode("utf-8"),
    )
