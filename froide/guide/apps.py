from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class GuideConfig(AppConfig):
    name = 'froide.guide'
    verbose_name = _('Guide')

    def ready(self):
        from . import signals  # noqa
