import json
from datetime import timedelta

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.dispatch import Signal
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from parler.models import TranslatableModel, TranslatedFields
from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase
from taggit.utils import edit_string_for_tags
from treebeard.mp_tree import MP_Node, MP_NodeManager

from froide.georegion.models import GeoRegion
from froide.helper.csv_utils import export_csv
from froide.helper.date_utils import (
    calculate_month_range_de,
    calculate_workingday_range,
)
from froide.helper.templatetags.markup import markdown

DEFAULT_LAW = settings.FROIDE_CONFIG.get("default_law", 1)


def get_applicable_law(pb=None, law_type=None):
    if pb is not None:
        pb_laws = pb.laws.all()
        juris_laws = FoiLaw.objects.filter(jurisdiction=pb.jurisdiction)
        # Check pb laws and then, if empty, pb juris laws
        for qs in (pb_laws, juris_laws):
            if law_type is not None:
                qs = qs.filter(law_type__contains=law_type)
            # Prefer meta laws
            qs = qs.order_by("-meta", "-priority")
            if qs:
                try:
                    return qs[0]
                except IndexError:
                    pass

    try:
        return FoiLaw.objects.get(id=DEFAULT_LAW)
    except FoiLaw.DoesNotExist:
        return None


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


class FoiLaw(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(_("Name"), max_length=255),
        slug=models.SlugField(_("Slug"), max_length=255),
        description=models.TextField(_("Description"), blank=True),
        long_description=models.TextField(_("Website Text"), blank=True),
        legal_text=models.TextField(_("Legal Text"), blank=True),
        request_note=models.TextField(_("request note"), blank=True),
        letter_start=models.TextField(_("Start of Letter"), blank=True),
        letter_end=models.TextField(_("End of Letter"), blank=True),
        refusal_reasons=models.TextField(_("refusal reasons"), blank=True),
        overdue_reply=models.TextField(_("overdue reply"), blank=True),
    )

    created = models.DateField(_("Creation Date"), blank=True, null=True)
    updated = models.DateField(_("Updated Date"), blank=True, null=True)

    meta = models.BooleanField(_("Meta Law"), default=False)
    law_type = models.CharField(_("law type"), max_length=255, blank=True)
    combined = models.ManyToManyField(
        "FoiLaw", verbose_name=_("Combined Laws"), blank=True
    )
    jurisdiction = models.ForeignKey(
        Jurisdiction,
        verbose_name=_("Jurisdiction"),
        null=True,
        on_delete=models.SET_NULL,
        blank=True,
    )
    priority = models.SmallIntegerField(_("Priority"), default=3)
    url = models.CharField(_("URL"), max_length=255, blank=True)
    scale_of_fees = models.CharField(_("Scale of fees URL"), max_length=255, blank=True)
    max_response_time = models.IntegerField(
        _("Maximal Response Time"), null=True, blank=True, default=30
    )
    max_response_time_unit = models.CharField(
        _("Unit of Response Time"),
        blank=True,
        max_length=32,
        default="day",
        choices=(
            ("day", _("Day(s)")),
            ("working_day", _("Working Day(s)")),
            ("month_de", _("Month(s) (DE)")),
        ),
    )
    mediator = models.ForeignKey(
        "PublicBody",
        verbose_name=_("Mediator"),
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="mediating_laws",
    )
    email_only = models.BooleanField(_("E-Mail only"), default=False)
    requires_signature = models.BooleanField(_("Requires signature"), default=False)
    site = models.ForeignKey(
        Site,
        verbose_name=_("Site"),
        null=True,
        on_delete=models.SET_NULL,
        default=settings.SITE_ID,
    )

    class Meta:
        verbose_name = _("Freedom of Information Law")
        verbose_name_plural = _("Freedom of Information Laws")
        ordering = (
            "-meta",
            "-priority",
        )

    def __str__(self):
        return "%s (%s)" % (self.name, self.jurisdiction if self.jurisdiction else "")

    def get_absolute_url(self):
        return reverse("publicbody-foilaw-show", kwargs={"slug": self.slug})

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    @property
    def request_note_html(self):
        return markdown(self.request_note)

    @property
    def description_html(self):
        return markdown(self.description)

    @property
    def address_required(self):
        return not self.email_only

    def get_refusal_reason_choices(self):
        not_applicable = [("n/a", _("No law can be applied"))]
        if self.meta:
            return not_applicable + [
                (c[0], "%s: %s" % (law.name, c[1]))
                for law in self.combined.all()
                for c in law.get_refusal_reason_choices()[1:]
            ]
        else:
            return not_applicable + [
                (x, Truncator(x).words(12)) for x in self.refusal_reasons.splitlines()
            ]

    def as_data(self, request=None):
        from froide.helper.api_utils import get_fake_api_context

        from .api_views import FoiLawSerializer

        if request is None:
            ctx = get_fake_api_context()
        else:
            ctx = {"request": request}
        return FoiLawSerializer(self, context=ctx).data

    def calculate_due_date(self, date=None, value=None):
        if date is None:
            date = timezone.now()
        if value is None:
            value = self.max_response_time
        if self.max_response_time_unit == "month_de":
            return calculate_month_range_de(date, value)
        elif self.max_response_time_unit == "day":
            return date + timedelta(days=value)
        elif self.max_response_time_unit == "working_day":
            return calculate_workingday_range(date, value)


class PublicBodyTagManager(models.Manager):
    def get_topic_list(self):
        return (
            self.get_queryset()
            .filter(is_topic=True)
            .order_by("rank", "name")
            .annotate(num_publicbodies=models.Count("publicbodies"))
        )


class PublicBodyTag(TagBase):
    is_topic = models.BooleanField(_("as topic"), default=False)
    rank = models.SmallIntegerField(_("rank"), default=0)

    objects = PublicBodyTagManager()

    class Meta:
        verbose_name = _("Public Body Tag")
        verbose_name_plural = _("Public Body Tags")


class TaggedPublicBody(TaggedItemBase):
    tag = models.ForeignKey(
        PublicBodyTag, on_delete=models.CASCADE, related_name="publicbodies"
    )
    content_object = models.ForeignKey("PublicBody", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Tagged Public Body")
        verbose_name_plural = _("Tagged Public Bodies")


class CategoryManager(MP_NodeManager):
    def get_category_list(self):
        count = models.Count("categorized_publicbodies")
        return (
            self.get_queryset()
            .filter(depth=1, is_topic=True)
            .order_by("name")
            .annotate(num_publicbodies=count)
        )


class Category(TagBase, MP_Node):
    is_topic = models.BooleanField(_("as topic"), default=False)

    node_order_by = ["name"]
    objects = CategoryManager()

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def save(self, *args, **kwargs):
        if self.pk is None and kwargs.get("force_insert"):
            obj = Category.add_root(
                name=self.name, slug=self.slug, is_topic=self.is_topic
            )
            self.pk = obj.pk
        else:
            TagBase.save(self, *args, **kwargs)


class CategorizedPublicBody(TaggedItemBase):
    tag = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="categorized_publicbodies"
    )
    content_object = models.ForeignKey("PublicBody", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Categorized Public Body")
        verbose_name_plural = _("Categorized Public Bodies")


class ClassificationManager(MP_NodeManager):
    def get_list(self):
        count = models.Count("publicbody")
        return (
            self.get_queryset()
            .filter(depth=1)
            .order_by("name")
            .annotate(num_publicbodies=count)
        )


class Classification(MP_Node):
    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255)

    node_order_by = ["name"]
    objects = ClassificationManager()

    class Meta:
        verbose_name = _("classification")
        verbose_name_plural = _("classifications")

    def __str__(self):
        return self.name


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

    email = models.EmailField(_("Email"), blank=True, default="")
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
    tags = TaggableManager(through=TaggedPublicBody, blank=True)
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

    def get_email(self, law_type=None):
        if not law_type:
            return self.email
        if self.alternative_emails:
            return self.alternative_emails.get(law_type, self.email)
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
        from .api_views import PublicBodyListSerializer

        return self._as_data(PublicBodyListSerializer)

    def as_simple_data(self, request=None):
        from .api_views import SimplePublicBodySerializer

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
