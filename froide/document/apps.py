from django.apps import AppConfig
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class DocumentConfig(AppConfig):
    name = "froide.document"
    verbose_name = _("Document")

    def ready(self):
        import froide.document.signals  # noqa
        from froide.helper.search import search_registry

        search_registry.register(add_search)


def add_search(request):
    if request.user.is_staff:
        return {
            "title": _("Documents (beta)"),
            "name": "document",
            "url": reverse("document-search"),
        }
