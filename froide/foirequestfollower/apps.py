from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FoiRequestFollowerConfig(AppConfig):
    name = "froide.foirequestfollower"
    verbose_name = _("FOI Request Follower")

    def ready(self):
        import froide.foirequestfollower.listeners  # noqa
        from froide.api import api_router
        from froide.foirequest.models import FoiRequest
        from froide.follow.configuration import follow_registry

        from .api_views import FoiRequestFollowerViewSet
        from .configuration import FoiRequestFollowConfiguration

        api_router.register(
            r"following", FoiRequestFollowerViewSet, basename="following"
        )

        FoiRequest.made_private.connect(remove_followers)

        follow_registry.register(FoiRequestFollowConfiguration())


def remove_followers(sender=None, **kwargs):
    from .models import FoiRequestFollower

    FoiRequestFollower.objects.filter(content_object=sender).delete()
