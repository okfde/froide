from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible
from django.contrib.sites.models import Site
from django.dispatch import Signal
from django.contrib.sites.managers import CurrentSiteManager

from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase

from froide.team.models import Team


class TaggedFoiProject(TaggedItemBase):
    content_object = models.ForeignKey('FoiProject', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Project Tag')
        verbose_name_plural = _('Project Tags')


class FoiProjectManager(CurrentSiteManager):
    def get_for_user(self, user, **query_kwargs):
        qs = self.get_queryset()
        user_teams = Team.objects.get_for_user(user)
        qs = qs.filter(
            models.Q(user=user) |
            models.Q(team__in=user_teams),
            **query_kwargs
        )
        return qs


@python_2_unicode_compatible
class FoiProject(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_READY = 'ready'
    STATUS_COMPLETE = 'complete'
    STATUS_ASLEEP = 'asleep'

    STATUS_CHOICES = (
        (STATUS_PENDING, _('pending')),
        (STATUS_READY, _('ready')),
        (STATUS_COMPLETE, _('complete')),
        (STATUS_ASLEEP, _('asleep')),
    )

    title = models.CharField(_("Title"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)

    description = models.TextField(_("Description"), blank=True)

    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING
    )

    created = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    public = models.BooleanField(_("published?"), default=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("User"))
    team = models.ForeignKey(Team, null=True, blank=True,
            on_delete=models.SET_NULL, verbose_name=_("Team"))

    request_count = models.IntegerField(default=0)
    reference = models.CharField(_("Reference"), blank=True, max_length=255)
    tags = TaggableManager(through=TaggedFoiProject, blank=True)

    site = models.ForeignKey(Site, null=True,
            on_delete=models.SET_NULL, verbose_name=_("Site"))

    objects = FoiProjectManager()

    class Meta:
        verbose_name = _('FOI Project')
        verbose_name_plural = _('FOI Projects')
        ordering = ('last_update',)

    project_created = Signal(providing_args=[])

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('foirequest-project', kwargs={'slug': self.slug})

    def get_absolute_short_url(self):
        return reverse('foirequest-project_shortlink',
                kwargs={'obj_id': self.id})

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_absolute_domain_short_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_short_url())
