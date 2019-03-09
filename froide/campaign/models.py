from django.db import models
from django.utils.translation import ugettext_lazy as _


class CampaignManager(models.Manager):
    def get_filter_list(self):
        return super().get_queryset().filter(public=True)


class Campaign(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()

    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField(null=True)
    public = models.BooleanField(default=False)

    objects = CampaignManager()

    class Meta:
        verbose_name = _('campaign')
        verbose_name_plural = _('campaigns')

    def __str__(self):
        return self.name
