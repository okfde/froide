from django.apps import AppConfig
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class DocumentNoConfig(AppConfig):
    name = "froide.document"
    verbose_name = _("Document")


class DocumentConfig(AppConfig):
    name = "froide.document"
    verbose_name = _("Document")
    default = True

    def ready(self):
        import froide.document.signals  # noqa
        from froide.api import api_router
        from froide.helper.search import search_registry

        from .api_views import (
            DocumentCollectionViewSet,
            DocumentViewSet,
            PageAnnotationViewSet,
            PageViewSet,
        )

        search_registry.register(add_search)

        api_router.register(r"document", DocumentViewSet, basename="document")
        api_router.register(
            r"documentcollection",
            DocumentCollectionViewSet,
            basename="documentcollection",
        )
        api_router.register(r"page", PageViewSet, basename="page")
        api_router.register(
            r"pageannotation", PageAnnotationViewSet, basename="pageannotation"
        )


def add_search(request):
    return {
        "title": _("Documents"),
        "name": "document",
        "url": reverse("document-search"),
    }
