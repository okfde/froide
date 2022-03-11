from django.db import models
from django.utils.translation import gettext_lazy as _

from froide.foirequest.models import FoiRequest
from froide.follow.models import Follower


class FoiRequestFollower(Follower):
    content_object = models.ForeignKey(
        FoiRequest,
        on_delete=models.CASCADE,
        related_name="followers",
        verbose_name=_("Freedom of Information Request"),
    )

    class Meta(Follower.Meta):
        verbose_name = _("Request Follower")
        verbose_name_plural = _("Request Followers")
