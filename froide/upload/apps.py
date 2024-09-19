from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UploadConfig(AppConfig):
    name = "froide.upload"
    verbose_name = _("Upload")

    def ready(self) -> None:
        from froide.api import api_router

        from .api_views import UploadViewSet

        api_router.register(r"upload", UploadViewSet, basename="upload")
