from django.apps import AppConfig
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class PublicBodyNoConfig(AppConfig):
    name = "froide.publicbody"
    verbose_name = _("Public Body")


class PublicBodyConfig(AppConfig):
    name = "froide.publicbody"
    verbose_name = _("Public Body")
    default = True

    def ready(self):
        from froide.account import account_merged
        from froide.account.export import registry
        from froide.helper.search import search_registry

        from .utils import export_user_data

        registry.register(export_user_data)
        account_merged.connect(merge_user)
        search_registry.register(add_search)

        from froide.api import api_router

        from .api_views import (
            CategoryViewSet,
            ClassificationViewSet,
            FoiLawViewSet,
            JurisdictionViewSet,
            PublicBodyViewSet,
        )

        api_router.register(r"publicbody", PublicBodyViewSet, basename="publicbody")
        api_router.register(r"category", CategoryViewSet, basename="category")
        api_router.register(
            r"classification", ClassificationViewSet, basename="classification"
        )
        api_router.register(
            r"jurisdiction", JurisdictionViewSet, basename="jurisdiction"
        )
        api_router.register(r"law", FoiLawViewSet, basename="law")


def add_search(request):
    return {
        "name": "publicbody",
        "title": _("Public Bodies"),
        "url": reverse("publicbody-list"),
    }


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership

    from .models import ProposedPublicBody, PublicBody

    mapping = [
        (PublicBody, "_created_by"),
        (PublicBody, "_updated_by"),
        (ProposedPublicBody, "_created_by"),
        (ProposedPublicBody, "_updated_by"),
    ]

    for model, attr in mapping:
        move_ownership(model, attr, old_user, new_user)
