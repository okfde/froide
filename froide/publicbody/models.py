import json

from django.db import models
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.core.urlresolvers import reverse



class PublicBodyManager(CurrentSiteManager):
    def get_for_homepage(self, count=5):
        return self.get_query_set()[:count]

    def get_for_search_index(self):
        return self.get_query_set()

class FoiLaw(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255)
    description = models.TextField(blank=True)
    paragraph = models.TextField(blank=True)
    cite = models.TextField(blank=True)
    jurisdiction = models.CharField(max_length=255)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
            null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = _("Freedom of Information Law")
        verbose_name_plural = _("Freedom of Information Laws")

    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.jurisdiction)


class PublicBody(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    topic = models.CharField(_("Topic"), max_length=255, blank=True)
    url = models.URLField(_("URL"), blank=True, verify_exists=False)
    
    email = models.EmailField(_("Email"))
    contact = models.TextField(_("Contact"), blank=True)
    address = models.TextField(_("Address"), blank=True)
    website_dump = models.TextField(_("Website Dump"), null=True, blank=True)
    
    _created_by = models.ForeignKey(User, verbose_name=_("Created by"),
            blank=True, null=True, related_name='public_body_creators',
            on_delete=models.SET_NULL)
    _updated_by = models.ForeignKey(User, verbose_name=_("Updated by"),
            blank=True, null=True, related_name='public_body_updaters',
            on_delete=models.SET_NULL)
    
    number_of_requests = models.IntegerField(_("Number of requests"),
            default=0)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
            null=True, on_delete=models.SET_NULL)
    
    geography = models.CharField(_("Geography"), max_length=255)

    laws = models.ManyToManyField(FoiLaw, verbose_name=_("Freedom of Information Laws"))
    
    objects = PublicBodyManager()
    
    class Meta:
        verbose_name = _("Public Body")
        verbose_name_plural = _("Public Bodies")

    serializable_fields = ('name', 'slug',
            'description', 'topic', 'url', 'email', 'contact',
            'address', 'geography', 'domain')
        
    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.geography)

    @property
    def created_by(self):
        return self._created_by or AnonymousUser()

    @property
    def updated_by(self):
        return self._updated_by or AnonymousUser()

    @property
    def domain(self):
        if self.url:
            return self.url.split("/")[2]
        return None

    def get_absolute_url(self):
        return reverse('publicbody-show', kwargs={"slug": self.slug})

    def as_json(self):
        d = {}
        for field in self.serializable_fields:
            d[field] = getattr(self, field)
        return json.dumps(d)
