import re

from django.db import models
from django.template.loader import select_template
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group


class CampaignManager(models.Manager):
    def get_filter_list(self):
        return super().get_queryset().filter(public=True)

    def get_active(self):
        return super().get_queryset().filter(active=True)


class Campaign(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()

    ident = models.CharField(max_length=50, blank=True)

    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField(null=True)
    public = models.BooleanField(default=False)
    active = models.BooleanField(default=False)

    request_match = models.TextField(blank=True)
    request_hint = models.TextField(blank=True)

    group = models.ForeignKey(
        Group, null=True, blank=True,
        on_delete=models.SET_NULL
    )

    objects = CampaignManager()

    class Meta:
        verbose_name = _('campaign')
        verbose_name_plural = _('campaigns')

    def __str__(self):
        return self.name

    @property
    def banner_templates(self):
        return select_template([
            'campaign/%s/request_banner.html' % self.ident,
            'campaign/request_banner.html'
        ])

    def match_text(self, text):
        regex_list = self.request_match
        if not regex_list:
            return False
        return all(
            re.search(line, text, re.I | re.S)
            for line in regex_list.splitlines()
        )
