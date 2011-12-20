from django.db import models
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager

from foirequest.models import FoiRequest


class FeaturedRequestManager(CurrentSiteManager):
    def getFeatured(self):
        try:
            return self.get_query_set().order_by("-timestamp").select_related('request', 'request__publicbody')[0]
        except (self.model.DoesNotExist, IndexError):
            return None


class FeaturedRequest(models.Model):
    request = models.ForeignKey(FoiRequest,
            verbose_name=_("Featured Request"))
    timestamp = models.DateTimeField()
    title = models.CharField(max_length=255)
    text = models.TextField()
    url = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(User, null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("User"))
    site = models.ForeignKey(Site, null=True,
            on_delete=models.SET_NULL, verbose_name=_("Site"))

    objects = FeaturedRequestManager()
