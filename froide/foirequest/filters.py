from collections import namedtuple

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext

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

FoiRequestFilter = namedtuple("FoiRequestFilter", "slug filter key label description")


def make_filter(slug, filter_func, key):
    return FoiRequestFilter(
        slug=slug,
        filter=filter_func,
        key=key,
        label=key.label,
        description=FoiRequest.STATUS_RESOLUTION_DICT[key].description,
    )


FOIREQUEST_FILTERS = [
    make_filter(
        pgettext("URL part", "awaiting-classification"),
        status_filter,
        FoiRequest.STATUS.AWAITING_CLASSIFICATION,
    ),
    make_filter(
        pgettext("URL part", "successful"),
        resolution_filter,
        FoiRequest.RESOLUTION.SUCCESSFUL,
    ),
    make_filter(
        pgettext("URL part", "partially-successful"),
        resolution_filter,
        FoiRequest.RESOLUTION.PARTIALLY_SUCCESSFUL,
    ),
    make_filter(
        pgettext("URL part", "refused"),
        resolution_filter,
        FoiRequest.RESOLUTION.REFUSED,
    ),
    make_filter(
        pgettext("URL part", "withdrawn"),
        resolution_filter,
        FoiRequest.RESOLUTION.USER_WITHDREW,
    ),
    make_filter(
        pgettext("URL part", "withdrawn-costs"),
        resolution_filter,
        FoiRequest.RESOLUTION.USER_WITHDREW_COSTS,
    ),
    make_filter(
        pgettext("URL part", "awaiting-response"),
        status_filter,
        FoiRequest.STATUS.AWAITING_RESPONSE,
    ),
    make_filter(
        pgettext("URL part", "overdue"),
        (
            lambda x: Q("range", due_date={"lt": timezone.now()})
            & Q("term", status="awaiting_response")
        ),
        FoiRequest.FILTER_STATUS.OVERDUE,
    ),
    make_filter(
        pgettext("URL part", "asleep"), status_filter, FoiRequest.STATUS.ASLEEP
    ),
    make_filter(
        pgettext("URL part", "not-held"),
        resolution_filter,
        FoiRequest.RESOLUTION.NOT_HELD,
    ),
    FoiRequestFilter(
        slug=pgettext("URL part", "has-fee"),
        filter=lambda x: Q("range", costs={"gt": 0}),
        key=None,
        label=_("Fee charged"),
        description=_("This request is connected with a fee."),
    ),
]

FOIREQUEST_FILTER_CHOICES = [(x.slug, x.label) for x in FOIREQUEST_FILTERS]
FOIREQUEST_FILTER_DICT = dict([(x.slug, x) for x in FOIREQUEST_FILTERS])
REVERSE_FILTER_DICT = dict([(str(x.key), x) for x in FOIREQUEST_FILTERS])

FOIREQUEST_LIST_FILTER_CHOICES = [
    x
    for x in FOIREQUEST_FILTER_CHOICES
    if x[0] not in {pgettext("URL part", "awaiting-classification")}
]


def get_active_filters(data):
    for key in FILTER_ORDER:
        if not data.get(key):
            continue
        yield key
        sub_filters = SUB_FILTERS.get(key, ())
        for sub_key in sub_filters:
            if data.get(sub_key):
                yield sub_key
                break
        break


def get_filter_data(filter_kwargs, data):
    query = {}
    for key in get_active_filters(filter_kwargs):
        query[key] = filter_kwargs[key]
    data.update(query)
    return data


class DropDownStatusFilterWidget(DropDownFilterWidget):
    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super(DropDownStatusFilterWidget, self).create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        if value:
            status = FOIREQUEST_FILTER_DICT[value].key
            option["icon"] = "status-%s" % status
        return option


class BaseFoiRequestFilterSet(BaseSearchFilterSet):
    query_fields = ["title^5", "description^3", "content"]

    q = django_filters.CharFilter(
        method="auto_query",
        widget=forms.TextInput(
            attrs={"placeholder": _("Search requests"), "class": "form-control"}
        ),
    )
    FOIREQUEST_FILTER_DICT = FOIREQUEST_FILTER_DICT
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
        method="filter_first",
        widget=DateRangeWidget,
    )
    last = django_filters.DateFromToRangeFilter(
        method="filter_last", widget=DateRangeWidget
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

    class Meta:
        model = FoiRequest
        fields = [
            "q",
            "status",
            "jurisdiction",
            "campaign",
            "category",
            "classification",
            "tag",
            "publicbody",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.view is not None:
            self.filters["status"].field.widget.get_url = self.view.make_filter_url

    def filter_status(self, qs, name, value):
        entry = self.FOIREQUEST_FILTER_DICT[value]
        return qs.filter(entry.filter(entry.key))

    def filter_jurisdiction(self, qs, name, value):
        return qs.filter(jurisdiction=value.id)

    def filter_campaign(self, qs, name, value):
        if value == "-":
            return qs.filter(Q("bool", must_not={"exists": {"field": "campaign"}}))
        return qs.filter(campaign=value.id)

    def filter_category(self, qs, name, value):
        return qs.filter(categories=value.id)

    def filter_classification(self, qs, name, value):
        return qs.filter(classification=value.id)

    def filter_tag(self, qs, name, value):
        return qs.filter(tags=value.id)

    def filter_publicbody(self, qs, name, value):
        return qs.filter(publicbody=value.id)

    def filter_user(self, qs, name, value):
        return qs.filter(user=value.id)

    def filter_organization(self, qs, name, value):
        all_members = list(
            value.active_memberships.filter(user__private=False).values_list(
                "user_id", flat=True
            )
        )
        filtered_qs = qs.filter(user=all_members)
        return filtered_qs

    def filter_first(self, qs, name, value):
        range_kwargs = {}
        if value.start is not None:
            range_kwargs["gte"] = value.start
        if value.stop is not None:
            range_kwargs["lte"] = value.stop

        return qs.filter(Q("range", first_message=range_kwargs))

    def filter_last(self, qs, name, value):
        range_kwargs = {}
        if value.start is not None:
            range_kwargs["gte"] = value.start
        if value.stop is not None:
            range_kwargs["lte"] = value.stop
        return qs.filter(Q("range", last_message=range_kwargs))

    def add_sort(self, qs, name, value):
        if value:
            return qs.add_sort("%s_message" % value)
        return qs


class FoiRequestFilterSet(BaseFoiRequestFilterSet):
    pass
