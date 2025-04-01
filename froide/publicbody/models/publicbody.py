from typing import Optional

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.dispatch import Signal
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase
from taggit.utils import edit_string_for_tags

from froide.georegion.models import GeoRegion
from froide.helper.csv_utils import export_csv
from froide.helper.templatetags.markup import markdown

from .category import Category
from .classification import Classification
from .foilaw import FoiLaw, get_applicable_law
from .jurisdiction import Jurisdiction


class CategorizedPublicBody(TaggedItemBase):
    tag = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="categorized_publicbodies"
    )
    content_object = models.ForeignKey("PublicBody", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Categorized Public Body")
        verbose_name_plural = _("Categorized Public Bodies")


class PublicBodyManager(CurrentSiteManager):
    def get_queryset(self):
        return (
            super(PublicBodyManager, self)
            .get_queryset()
            .exclude(email="")
            .filter(email__isnull=False, confirmed=True)
        )

    def get_list(self):
        return (
            self.get_queryset()
            .filter(jurisdiction__hidden=False)
            .select_related("jurisdiction")
        )

    def get_for_search_index(self):
        return self.get_queryset()


class PublicBody(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    other_names = models.TextField(_("Other names"), default="", blank=True)
    slug = models.SlugField(_("Slug"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    url = models.URLField(_("URL"), null=True, blank=True, max_length=500)

    parent = models.ForeignKey(
        "PublicBody",
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    root = models.ForeignKey(
        "PublicBody",
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="descendants",
    )
    depth = models.SmallIntegerField(default=0)

    classification = models.ForeignKey(
        Classification, null=True, blank=True, on_delete=models.SET_NULL
    )

    email = models.EmailField(_("Email"), blank=True, default="", max_length=255)
    fax = models.CharField(max_length=50, blank=True)
    contact = models.TextField(_("Contact"), blank=True)
    address = models.TextField(_("Address"), blank=True)
    website_dump = models.TextField(_("Website Dump"), null=True, blank=True)
    request_note = models.TextField(_("request note"), blank=True)
    source_reference = models.CharField(
        _("source reference"), max_length=255, blank=True
    )
    alternative_emails = models.JSONField(null=True, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)

    change_history = models.JSONField(default=list, blank=True)

    file_index = models.CharField(_("file index"), max_length=1024, blank=True)
    org_chart = models.CharField(_("organisational chart"), max_length=1024, blank=True)

    _created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Created by"),
        blank=True,
        null=True,
        related_name="public_body_creators",
        on_delete=models.SET_NULL,
    )
    _updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Updated by"),
        blank=True,
        null=True,
        related_name="public_body_updaters",
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(_("Created at"), default=timezone.now)
    updated_at = models.DateTimeField(_("Updated at"), default=timezone.now)
    confirmed = models.BooleanField(_("confirmed"), default=True)

    number_of_requests = models.IntegerField(_("Number of requests"), default=0)
    site = models.ForeignKey(
        Site,
        verbose_name=_("Site"),
        null=True,
        on_delete=models.SET_NULL,
        default=settings.SITE_ID,
    )

    wikidata_item = models.CharField(_("Wikidata item"), max_length=50, blank=True)

    jurisdiction = models.ForeignKey(
        Jurisdiction,
        verbose_name=_("Jurisdiction"),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    geo = models.PointField(null=True, blank=True, geography=True)
    regions = models.ManyToManyField(GeoRegion, blank=True)

    laws = models.ManyToManyField(
        FoiLaw, blank=True, verbose_name=_("Freedom of Information Laws")
    )
    categories = TaggableManager(
        through=CategorizedPublicBody, verbose_name=_("categories"), blank=True
    )

    non_filtered_objects = models.Manager()
    objects = PublicBodyManager()
    published = objects

    proposal_added = Signal()  # args: ['user']
    proposal_rejected = Signal()  # args: ['user']
    proposal_accepted = Signal()  # args: ['user']
    change_proposal_added = Signal()  # args: ['user']
    change_proposal_accepted = Signal()  # args: ['user']

    class Meta:
        ordering = ("name",)
        verbose_name = _("Public Body")
        verbose_name_plural = _("Public Bodies")
        permissions = (("moderate", _("Can moderate public bodies")),)

    serializable_fields = (
        "id",
        "name",
        "slug",
        "request_note_html",
        "description",
        "url",
        "email",
        "contact",
        "address",
        "domain",
        "number_of_requests",
    )

    def __str__(self):
        return self.name

    @property
    def created_by(self):
        return self._created_by

    @property
    def updated_by(self):
        return self._updated_by

    @property
    def domain(self):
        if self.url and self.url.count("/") > 1:
            return self.url.split("/")[2]
        return None

    @property
    def all_names(self):
        names = [self.name, self.other_names]
        if self.jurisdiction:
            names.extend([self.jurisdiction.name, self.jurisdiction.slug])
        return " ".join(names)

    @property
    def request_note_html(self):
        return markdown(self.request_note)

    @property
    def tag_list(self):
        return edit_string_for_tags(self.tags.all())

    @property
    def category_list(self):
        return [c.name for c in self.categories.all()]

    @property
    def default_law(self):
        # FIXME: Materialize this?
        return self.get_applicable_law()

    @property
    def change_proposal_count(self):
        return self.change_proposals.count()

    @property
    def reason(self):
        try:
            return self.change_history[-1].get("data", {}).get("reason", "")
        except IndexError:
            return ""

    def get_applicable_law(self, law_type=None):
        return get_applicable_law(pb=self, law_type=law_type)

    def get_absolute_url(self):
        return reverse("publicbody-show", kwargs={"slug": self.slug, "pk": self.id})

    def get_absolute_short_url(self):
        return reverse("publicbody-publicbody_shortlink", kwargs={"obj_id": self.pk})

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_absolute_domain_short_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_short_url())

    def get_email(
        self, law_type: Optional[str] = None, responsibility: Optional[Category] = None
    ):
        if not law_type and not responsibility:
            return self.email
        if self.alternative_emails:
            if responsibility:
                email = self.alternative_emails.get(responsibility.name)
            if email is None and law_type:
                email = self.alternative_emails.get(law_type, self.email)
            return email
        return self.email

    def get_mediator(self):
        law = self.default_law
        if law is None:
            return None
        return law.mediator

    def get_label(self):
        return mark_safe(
            '%(name)s - <a href="%(url)s" target="_blank" '
            'class="info-link">%(detail)s</a>'
            % {
                "name": escape(self.name),
                "url": self.get_absolute_url(),
                "detail": _("More Info"),
            }
        )

    def _as_data(self, serializer_klass, request=None):
        from froide.helper.api_utils import get_fake_api_context

        if request is None:
            ctx = get_fake_api_context()
        else:
            ctx = {"request": request}
        return serializer_klass(self, context=ctx).data

    def as_data(self, request=None):
        from ..serializers import PublicBodyListSerializer

        return self._as_data(PublicBodyListSerializer)

    def as_simple_data(self, request=None):
        from ..serializers import SimplePublicBodySerializer

        return self._as_data(SimplePublicBodySerializer)

    @property
    def children_count(self):
        return len(PublicBody.objects.filter(parent=self))

    @classmethod
    def export_csv(cls, queryset):
        fields = (
            "id",
            "name",
            "email",
            "fax",
            "contact",
            "address",
            "url",
            (
                "classification",
                lambda x: x.classification.name if x.classification else None,
            ),
            "jurisdiction__slug",
            ("categories", lambda x: edit_string_for_tags(x.categories.all())),
            "other_names",
            "website_dump",
            "description",
            "request_note",
            "parent__id",
            ("regions", lambda obj: ",".join(str(x.id) for x in obj.regions.all())),
        )

        return export_csv(queryset, fields)

    def confirm(self, user=None):
        if self.confirmed:
            return None
        self.confirmed = True
        self.save()
        self.proposal_accepted.send(sender=self, user=user)
        counter = 0
        for request in self.foirequest_set.all():
            if request.confirmed_public_body():
                counter += 1
        return counter


class ProposedPublicBodyManager(CurrentSiteManager):
    def get_queryset(self):
        return super().get_queryset().filter(confirmed=False)


class ProposedPublicBody(PublicBody):
    objects = ProposedPublicBodyManager()

    class Meta:
        proxy = True
        ordering = ("-created_at",)
        verbose_name = _("Proposed Public Body")
        verbose_name_plural = _("Proposed Public Bodies")
