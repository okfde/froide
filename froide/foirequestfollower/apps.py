from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FoiRequestFollowerConfig(AppConfig):
    name = "froide.foirequestfollower"
    verbose_name = _("FOI Request Follower")

    def ready(self):
        import froide.foirequestfollower.listeners  # noqa
        from froide.foirequest.models import FoiRequest
        from froide.follow.configuration import follow_registry

        from .configuration import FoiRequestFollowConfiguration

        FoiRequest.made_private.connect(remove_followers)

        follow_registry.register(FoiRequestFollowConfiguration())


def remove_followers(sender=None, **kwargs):
    from .models import FoiRequestFollower

    FoiRequestFollower.objects.filter(content_object=sender).delete()
