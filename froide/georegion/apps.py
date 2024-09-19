from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GeoRegionConfig(AppConfig):
    name = "froide.georegion"
    verbose_name = _("Geo Region")

    def ready(self):
        from froide.api import api_router
        from froide.georegion.api_views import GeoRegionViewSet

        api_router.register(r"georegion", GeoRegionViewSet, basename="georegion")
