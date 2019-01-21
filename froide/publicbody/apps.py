from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class PublicBodyConfig(AppConfig):
    name = 'froide.publicbody'
    verbose_name = _('Public Body')

    def ready(self):
        from froide.account.export import registry
        from .utils import export_user_data

        registry.register(export_user_data)
