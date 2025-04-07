import json

from django.conf import settings
from django.contrib.gis.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase

from froide.georegion.models import GeoRegion

from .category import Category
from .classification import Classification
from .jurisdiction import Jurisdiction
from .publicbody import PublicBody


class CategorizedPublicBodyChangeProposal(TaggedItemBase):
    tag = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="categorized_publicbody_change_proposals",
    )
    content_object = models.ForeignKey(
        "PublicBodyChangeProposal", on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _("Categorized Public Body Change Proposal")
        verbose_name_plural = _("Categorized Public Body Change Proposals")


class PublicBodyChangeProposal(models.Model):
    publicbody = models.ForeignKey(
        PublicBody, on_delete=models.CASCADE, related_name="change_proposals"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(_("Created at"), default=timezone.now)
    reason = models.TextField(blank=True)

    name = models.CharField(_("Name"), max_length=255)
    other_names = models.TextField(_("Other names"), default="", blank=True)

    url = models.URLField(_("URL"), null=True, blank=True, max_length=500)

    classification = models.ForeignKey(
        Classification, null=True, blank=True, on_delete=models.SET_NULL
    )

    email = models.EmailField(_("Email"), blank=True, default="")
    fax = models.CharField(max_length=50, blank=True)
    contact = models.TextField(_("Contact"), blank=True)
    address = models.TextField(_("Address"), blank=True)

    file_index = models.URLField(_("file index"), max_length=1024, blank=True)
    org_chart = models.URLField(_("organisational chart"), max_length=1024, blank=True)

    jurisdiction = models.ForeignKey(
        Jurisdiction,
        verbose_name=_("Jurisdiction"),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    geo = models.PointField(null=True, blank=True, geography=True)
    regions = models.ManyToManyField(GeoRegion, blank=True)

    categories = TaggableManager(
        through=CategorizedPublicBodyChangeProposal,
        verbose_name=_("categories"),
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Proposed Public Body Change")
        verbose_name_plural = _("Proposed Public Body Changes")
        constraints = [
            models.UniqueConstraint(
                fields=["publicbody", "user"], name="unique_publicbody_user_change"
            )
        ]

    def __str__(self):
        return "{} ({})".format(self.publicbody, self.user)

    def as_form_data(self):
        def field_data(field):
            value = getattr(self, field)
            return {
                "value": value,
                "label": value,
                "is_changed": value != getattr(self.publicbody, field),
            }

        regions = self.regions.all()
        categories = self.categories.all()
        return {
            "name": field_data("name"),
            "other_names": field_data("other_names"),
            "url": field_data("url"),
            "classification": {
                "label": str(self.classification),
                "value": self.classification_id,
                "is_changed": self.classification_id
                != self.publicbody.classification_id,
            },
            "email": field_data("email"),
            "reason": field_data("reason"),
            "fax": field_data("fax"),
            "contact": field_data("contact"),
            "address": field_data("address"),
            "file_index": field_data("file_index"),
            "org_chart": field_data("org_chart"),
            "jurisdiction": {
                "label": str(self.jurisdiction),
                "value": self.jurisdiction_id,
                "is_changed": self.jurisdiction_id != self.publicbody.jurisdiction_id,
            },
            "regions": {
                "label": ", ".join(str(x) for x in regions),
                "value": json.dumps(
                    [{"label": str(x), "value": x.id} for x in regions]
                ),
                "is_changed": set(regions) != set(self.publicbody.regions.all()),
            },
            "categories": {
                "label": ", ".join(str(x) for x in categories),
                "value": json.dumps(
                    [{"label": x.name, "value": x.name} for x in categories]
                ),
                "is_changed": set(categories) != set(self.publicbody.categories.all()),
            },
        }
