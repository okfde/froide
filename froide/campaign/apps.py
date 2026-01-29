from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CampaignConfig(AppConfig):
    name = "froide.campaign"
    verbose_name = _("Campaign")

    def ready(self):
        from froide.api import api_router
        from froide.foirequest.models import FoiRequest

        from .api_views import CampaignViewSet
        from .listeners import connect_campaign

        api_router.register(r"campaign", CampaignViewSet, basename="campaign")

        FoiRequest.request_sent.connect(connect_campaign)
