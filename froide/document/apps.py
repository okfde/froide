from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class DocumentConfig(AppConfig):
    name = 'froide.document'
    verbose_name = _('Document')

    def ready(self):
        import froide.document.signals  # noqa
