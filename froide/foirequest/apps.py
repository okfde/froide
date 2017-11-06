from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FoiRequestConfig(AppConfig):
    name = 'froide.foirequest'
    verbose_name = _('FOI Request')

    def ready(self):
        import froide.foirequest.signals  # noqa
