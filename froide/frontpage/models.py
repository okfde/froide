from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager

from froide.foirequest.models import FoiRequest


class FeaturedRequestManager(CurrentSiteManager):
    def getFeatured(self):
        try:
            return self.get_query_set().order_by("-timestamp").select_related('request', 'request__publicbody')[0]
        except IndexError:
            return None


class FeaturedRequest(models.Model):
    request = models.ForeignKey(FoiRequest,
            verbose_name=_("Featured Request"),
            null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(_("Timestamp"))
    title = models.CharField(_("Title"), max_length=255)
    text = models.TextField(_("Text"))
    url = models.CharField(_("URL"), max_length=255, blank=True)
    user = models.ForeignKey(User, null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("User"))
    site = models.ForeignKey(Site, null=True,
            on_delete=models.SET_NULL, verbose_name=_("Site"))

    objects = FeaturedRequestManager()

    class Meta:
        ordering = ('-timestamp',)
        get_latest_by = 'timestamp'
        verbose_name = _('Featured Request')
        verbose_name_plural = _('Featured Requests')
