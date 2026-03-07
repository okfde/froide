from collections import namedtuple
from functools import cache

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

import django_filters
from elasticsearch_dsl.query import Q
from taggit.models import Tag

from froide.account.models import User
from froide.campaign.models import Campaign
from froide.helper.search.filters import BaseSearchFilterSet
from froide.helper.widgets import BootstrapSelect, DateRangeWidget
from froide.organization.models import Organization
from froide.publicbody.models import Category, Classification, Jurisdiction, PublicBody

from .models import FoiRequest
from .widgets import DropDownFilterWidget


def resolution_filter(x):
    return Q("term", resolution=x)


def status_filter(x):
    return Q("term", status=x)


FILTER_ORDER = ("jurisdiction", "publicbody", "status", "category", "tag")
SUB_FILTERS = {"jurisdiction": ("status", "category", "tag", "publicbody")}

FoiRequestFilter = namedtuple(
    "FoiRequestFilter", "slug url_part filter key label description"
)


def make_filter(slug, url_part, filter_func, key):
    return FoiRequestFilter(
        slug=slug,
        url_part=url_part,
        filter=filter_func,
        key=key,
        label=key.label,
        description=FoiRequest.STATUS_RESOLUTION_DICT[key].description,
    )


FOIREQUEST_FILTERS = [
    make_filter(
        pgettext_lazy("slug", "awaiting-classification"),
        pgettext_lazy("URL part", "^(?P<status>awaiting-classification)/"),
        status_filter,
        FoiRequest.STATUS.AWAITING_CLASSIFICATION,
    ),
    make_filter(
        pgettext_lazy("slug", "successful"),
        pgettext_lazy("URL part", "^(?P<status>successful)/"),
        resolution_filter,
        FoiRequest.RESOLUTION.SUCCESSFUL,
    ),
    make_filter(
        pgettext_lazy("slug", "partially-successful"),
        pgettext_lazy("URL part", "^(?P<status>partially-successful)/"),
        resolution_filter,
        FoiRequest.RESOLUTION.PARTIALLY_SUCCESSFUL,
    ),
    make_filter(
        pgettext_lazy("slug", "refused"),
        pgettext_lazy("URL part", "^(?P<status>refused)/"),
        resolution_filter,
        FoiRequest.RESOLUTION.REFUSED,
    ),
    make_filter(
        pgettext_lazy("slug", "withdrawn"),
        pgettext_lazy("URL part", "^(?P<status>withdrawn)/"),
        resolution_filter,
        FoiRequest.RESOLUTION.USER_WITHDREW,
    ),
    make_filter(
        pgettext_lazy("slug", "withdrawn-costs"),
        pgettext_lazy("URL part", "^(?P<status>withdrawn-costs)/"),
        resolution_filter,
        FoiRequest.RESOLUTION.USER_WITHDREW_COSTS,
    ),
    make_filter(
        pgettext_lazy("slug", "awaiting-response"),
        pgettext_lazy("URL part", "^(?P<status>awaiting-response)/"),
        status_filter,
        FoiRequest.STATUS.AWAITING_RESPONSE,
    ),
    make_filter(
        pgettext_lazy("slug", "overdue"),
        pgettext_lazy("URL part", "^(?P<status>overdue)/"),
        (
            lambda x: Q("range", due_date={"lt": timezone.now()})
            & Q("term", status="awaiting_response")
        ),
        FoiRequest.FILTER_STATUS.OVERDUE,
    ),
    make_filter(
        pgettext_lazy("slug", "asleep"),
        pgettext_lazy("URL part", "^(?P<status>asleep)/"),
        status_filter,
        FoiRequest.STATUS.ASLEEP,
    ),
    make_filter(
        pgettext_lazy("slug", "not-held"),
        pgettext_lazy("URL part", "^(?P<status>not-held)/"),
        resolution_filter,
        FoiRequest.RESOLUTION.NOT_HELD,
    ),
    FoiRequestFilter(
        slug=pgettext_lazy("slug", "has-fee"),
        url_part=pgettext_lazy("URL part", "^(?P<status>has-fee)/"),
        filter=lambda x: Q("range", costs={"gt": 0}),
        key=None,
        label=_("Fee charged"),
        description=_("This request is connected with a fee."),
    ),
]

FOIREQUEST_FILTER_CHOICES = [(x.slug, x.label) for x in FOIREQUEST_FILTERS]
REVERSE_FILTER_DICT = {str(x.key): x for x in FOIREQUEST_FILTERS}

FOIREQUEST_LIST_FILTER_CHOICES = [
    x
    for x in FOIREQUEST_FILTER_CHOICES
    if x[0] not in {pgettext_lazy("slug", "awaiting-classification")}
]


def get_status_filter_by_slug(slug):
    for status_filter in FOIREQUEST_FILTERS:
        if status_filter.slug == slug:
            return status_filter


# jurisdictions seldomly change, so it's okay to cache until app restart
@cache
def get_jurisdictions_by_rank(rank: int) -> list[int]:
    return list(
        Jurisdiction.objects.get_visible()
        .filter(rank=rank)
        .values_list("id", flat=True)
    )


class DropDownStatusFilterWidget(DropDownFilterWidget):
    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super(DropDownStatusFilterWidget, self).create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        if value:
            status = get_status_filter_by_slug(value).key
            option["icon"] = "status-%s" % status
        return option


class BaseFoiRequestFilterSet(BaseSearchFilterSet):
    query_fields = ["title^5", "description^3", "content"]

    q = django_filters.CharFilter(
        method="auto_query",
        widget=forms.TextInput(
            attrs={"placeholder": _("Search requests"), "class": "form-control"}
        ),
        label=_("Search Term"),
    )
    status = django_filters.ChoiceFilter(
        choices=FOIREQUEST_LIST_FILTER_CHOICES,
        label=_("status"),
        empty_label=_("any status"),
        widget=DropDownStatusFilterWidget(
            attrs={"label": _("status"), "class": "form-control"}
        ),
        method="filter_status",
    )
    jurisdiction = django_filters.ModelChoiceFilter(
        queryset=Jurisdiction.objects.get_visible(),
        to_field_name="slug",
        label=_("jurisdiction"),
        empty_label=_("all jurisdictions"),
        widget=BootstrapSelect,
        method="filter_jurisdiction",
    )
    jurisdiction_rank = django_filters.NumberFilter(
        label=("jurisdiction rank"), method="filter_jurisdiction_rank"
    )
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.get_category_list(),
        to_field_name="slug",
        label=_("category"),
        empty_label=_("all categories"),
        widget=BootstrapSelect,
        method="filter_category",
    )
    classification = django_filters.ModelChoiceFilter(
        queryset=Classification.objects.all(),
        to_field_name="slug",
        empty_label=_("all classifications"),
        label=_("classification"),
        widget=BootstrapSelect,
        method="filter_classification",
    )
    campaign = django_filters.ModelChoiceFilter(
        queryset=Campaign.objects.get_filter_list(),
        to_field_name="slug",
        null_value="-",
        empty_label=_("all/no campaigns"),
        null_label=_("no campaign"),
        label=_("campaign"),
        widget=BootstrapSelect,
        method="filter_campaign",
    )
    tag = django_filters.ModelChoiceFilter(
        queryset=Tag.objects.all(),
        to_field_name="slug",
        method="filter_tag",
        widget=forms.HiddenInput(),
    )
    publicbody = django_filters.ModelChoiceFilter(
        queryset=PublicBody._default_manager.all(),
        to_field_name="slug",
        method="filter_publicbody",
        widget=forms.HiddenInput(),
    )
    user = django_filters.ModelChoiceFilter(
        queryset=User.objects.get_public_profiles(),
        to_field_name="username",
        method="filter_user",
        widget=forms.HiddenInput(),
    )
    organization = django_filters.ModelChoiceFilter(
        queryset=Organization.objects.get_public(),
        to_field_name="slug",
        method="filter_organization",
        widget=forms.HiddenInput(),
    )

    first = django_filters.DateFromToRangeFilter(
        method="filter_first", widget=DateRangeWidget, label=_("first message")
    )
    last = django_filters.DateFromToRangeFilter(
        method="filter_last", widget=DateRangeWidget, label=_("last message")
    )

    sort = django_filters.ChoiceFilter(
        choices=[
            ("-last", _("last message (newest first)")),
            ("last", _("last message (oldest first)")),
            ("-first", _("request date (newest first)")),
            ("first", _("request date (oldest first)")),
        ],
        label=_("sort"),
        empty_label=_("default sort"),
        widget=BootstrapSelect,
        method="add_sort",
    )
    hide_project_duplicates = django_filters.BooleanFilter(
        label=_("hide project duplicated"),
        method="filter_hide_project_duplicates",
    )

    class Meta:
        model = FoiRequest
        fields = [
            "q",
            "status",
            "jurisdiction",
            "jurisdiction_rank",
            "campaign",
            "category",
            "classification",
            "tag",
            "publicbody",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.view is not None:
            self.filters[
                "status"
            ].field.widget.get_url = self.view.search_manager.make_filter_url

    def filter_status(self, qs, name, value):
        entry = get_status_filter_by_slug(value)
        return self.apply_filter(qs, name, entry.filter(entry.key))

    def filter_jurisdiction(self, qs, name, value):
        return self.apply_filter(qs, name, jurisdiction=value.id)

    def filter_jurisdiction_rank(self, qs, name, value):
        return self.apply_filter(
            qs, name, jurisdiction=get_jurisdictions_by_rank(int(value))
        )

    def filter_campaign(self, qs, name, value):
        if value == "-":
            return self.apply_filter(
                qs, name, Q("bool", must_not={"exists": {"field": "campaign"}})
            )
        return self.apply_filter(qs, name, campaign=value.id)

    def filter_category(self, qs, name, value):
        return self.apply_filter(qs, name, categories=value.id)

    def filter_classification(self, qs, name, value):
        return self.apply_filter(qs, name, classification=value.id)

    def filter_tag(self, qs, name, value):
        return self.apply_filter(qs, name, tags=value.id)

    def filter_publicbody(self, qs, name, value):
        return self.apply_filter(qs, name, publicbody=value.id)

    def filter_user(self, qs, name, value):
        return self.apply_filter(qs, name, user=value.id)

    def filter_organization(self, qs, name, value):
        all_members = list(
            value.active_memberships.filter(user__private=False).values_list(
                "user_id", flat=True
            )
        )
        return self.apply_filter(qs, name, user=all_members)

    def filter_first(self, qs, name, value):
        range_kwargs = {}
        if value.start is not None:
            range_kwargs["gte"] = value.start
        if value.stop is not None:
            range_kwargs["lte"] = value.stop

        return self.apply_filter(qs, name, Q("range", first_message=range_kwargs))

    def filter_last(self, qs, name, value):
        range_kwargs = {}
        if value.start is not None:
            range_kwargs["gte"] = value.start
        if value.stop is not None:
            range_kwargs["lte"] = value.stop
        return self.apply_filter(qs, name, Q("range", last_message=range_kwargs))

    def add_sort(self, qs, name, value):
        if value:
            return qs.add_sort("%s_message" % value)
        return qs

    def filter_hide_project_duplicates(self, qs, name, value):
        if value:
            return self.apply_filter(
                qs,
                name,
                Q("bool", must_not={"exists": {"field": "project"}})
                | Q("term", project_order=0),
            )
        return qs


class FoiRequestFilterSet(BaseFoiRequestFilterSet):
    pass
