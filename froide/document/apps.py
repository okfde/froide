from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from django.urls import reverse


class DocumentConfig(AppConfig):
    name = 'froide.document'
    verbose_name = _('Document')

    def ready(self):
        import froide.document.signals  # noqa

        from froide.helper.search import search_registry

        search_registry.register(add_search)


def add_search(request):
    if request.user.is_staff:
        return {
            'title': _('Documents'),
            'name': 'document',
            'url': reverse('document-search')
        }
