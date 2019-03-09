from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CampaignConfig(AppConfig):
    name = 'froide.campaign'
    verbose_name = _('Campaign')
