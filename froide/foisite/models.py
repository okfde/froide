from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class FoiSite(models.Model):
    country_code = models.CharField(_('Country Code'), max_length=5)
    country_name = models.CharField(_('Country Name'), max_length=255)
    name = models.CharField(_('Name'), max_length=255)
    url = models.CharField(_('URL'), max_length=255)
    text = models.TextField(_('Text'), blank=True)
    enabled = models.BooleanField(_('Enabled'), default=True)

    class Meta:
        verbose_name = _('FOI Site')
        verbose_name_plural = _('FOI Sites')

    def __str__(self):
        return '%s (%s)' % (self.name, self.country_name)

    def save(self, *args, **kwargs):
        self.country_code = self.country_code.upper()
        super(FoiSite, self).save(*args, **kwargs)


try:
    from django.contrib.gis.geoip import GeoIP
except ImportError:
    GeoIP = None  # noqa


class SiteAdivsor(object):
    def __init__(self):
        self.geoip = GeoIP()
        self.sites = None

    def update(self):
        sites = FoiSite.objects.filter(enabled=True)
        self.sites = dict([(f.country_code, f) for f in sites])

    def refresh(self):
        self.sites = None

    def get_site(self, ip):
        if self.sites is None:
            self.update()
        result = self.geoip.country(ip)
        return self.sites.get(result['country_code'], None)


class DummyAdvisor(object):
    def refresh(self):
        pass

    def get_site(self, ip):
        pass


if GeoIP and getattr(settings, 'GEOIP_PATH', False):
    advisor = SiteAdivsor()
else:
    advisor = DummyAdvisor()


@receiver(models.signals.post_save, sender=FoiSite,
        dispatch_uid="foisite_saved")
def foisite_saved(instance=None, created=False, **kwargs):
    advisor.refresh()
