from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from froide.georegion.models import GeoRegion


class JurisdictionManager(models.Manager):
    def get_visible(self):
        return self.get_queryset().filter(hidden=False).order_by("rank", "name")

    def get_list(self):
        return self.get_visible().annotate(num_publicbodies=models.Count("publicbody"))


class Jurisdiction(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    hidden = models.BooleanField(_("Hidden"), default=False)
    rank = models.SmallIntegerField(default=1)
    region = models.ForeignKey(
        GeoRegion, null=True, on_delete=models.SET_NULL, blank=True
    )

    objects = JurisdictionManager()

    last_modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Jurisdiction")
        verbose_name_plural = _("Jurisdictions")
        ordering = (
            "rank",
            "name",
        )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("publicbody-show_jurisdiction", kwargs={"slug": self.slug})

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_all_laws(self):
        from .foilaw import FoiLaw

        laws = FoiLaw.objects.filter(jurisdiction=self)
        meta_ids = laws.filter(meta=True).values_list("combined", flat=True)
        meta_laws = FoiLaw.objects.filter(pk__in=meta_ids)
        return laws.union(meta_laws)

    def save(self, *args, **kwargs):
        if "update_fields" in kwargs:
            kwargs["update_fields"] = {"last_modified_at"}.union(
                kwargs["update_fields"]
            )

        super().save(*args, **kwargs)
