from datetime import timedelta

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from parler.models import TranslatableModel, TranslatedFields

from froide.helper.date_utils import (
    calculate_month_range_de,
    calculate_workingday_range,
)
from froide.helper.templatetags.markup import markdown

from .jurisdiction import Jurisdiction

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

        from ..serializers import FoiLawSerializer

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
