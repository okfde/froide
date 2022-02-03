from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CampaignConfig(AppConfig):
    name = "froide.campaign"
    verbose_name = _("Campaign")

    def ready(self):
        from froide.foirequest.models import FoiRequest

        from .listeners import connect_campaign

        FoiRequest.request_sent.connect(connect_campaign)
