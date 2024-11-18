from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

import django_filters
from elasticsearch_dsl.query import Q as ESQ
from filingcabinet.filters import DocumentFilter as FCDocumentFilter
from filingcabinet.models import CollectionDirectory, DocumentPortal, Page
from taggit.models import Tag

from froide.account.models import User
from froide.campaign.models import Campaign
from froide.foirequest.auth import get_read_foirequest_queryset
from froide.helper.auth import get_read_queryset
from froide.helper.search.filters import BaseSearchFilterSet
from froide.helper.widgets import BootstrapSelect, DateRangeWidget
from froide.publicbody.models import Jurisdiction, PublicBody

from .models import Document, DocumentCollection


def get_document_read_qs(request, read_unlisted=False):
    public_q = Q(public=True, listed=True)
    if read_unlisted:
        public_q = Q(public=True)
    return get_read_queryset(
        Document.objects.all(),
        request,
        has_team=True,
        public_q=public_q,
        scope="read:document",
    )


class DocumentFilter(FCDocumentFilter):
    publicbody = django_filters.ModelChoiceFilter(
        queryset=PublicBody.objects.all(),
        method="filter_publicbody",
    )
    foirequest = django_filters.ModelChoiceFilter(
        queryset=None,
        to_field_name="pk",
        method="filter_foirequest",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get("request")
        if request is None:
            request = self.view.request
        self.filters["foirequest"].queryset = get_read_foirequest_queryset(request)

    def filter_publicbody(self, qs, name, value):
        return qs.filter(publicbody=value)

    def filter_foirequest(self, qs, name, value):
        return qs.filter(foirequest=value)


def get_portal_queryset(request):
    if not request.user.is_crew:
        return DocumentPortal.objects.filter(public=True)
    return DocumentPortal.objects.all()


class PageDocumentFilterset(BaseSearchFilterSet):
    query_fields = ["title^3", "description^2", "content"]

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
    jurisdiction = django_filters.ModelChoiceFilter(
        queryset=Jurisdiction.objects.get_visible(),
        to_field_name="slug",
        empty_label=_("all jurisdictions"),
        label=_("jurisdiction"),
        widget=BootstrapSelect,
        method="filter_jurisdiction",
    )
    tag = django_filters.ModelChoiceFilter(
        queryset=Tag.objects.all(),
        to_field_name="slug",
        method="filter_tag",
        widget=forms.HiddenInput(),
    )
    foirequest = django_filters.ModelChoiceFilter(
        queryset=None,
        to_field_name="pk",
        method="filter_foirequest",
    )
    publicbody = django_filters.ModelChoiceFilter(
        queryset=PublicBody._default_manager.all(),
        to_field_name="pk",
        method="filter_publicbody",
        widget=forms.HiddenInput(),
    )
    collection = django_filters.ModelChoiceFilter(
        queryset=DocumentCollection.objects.filter(public=True),
        to_field_name="pk",
        method="filter_collection",
        widget=forms.HiddenInput(),
    )
    directory = django_filters.ModelChoiceFilter(
        queryset=CollectionDirectory.objects.all().select_related("collection"),
        to_field_name="pk",
        method="filter_directory",
        widget=forms.HiddenInput(),
    )
    portal = django_filters.ChoiceFilter(
        empty_label=_("Freedom of Information Requests"),
        null_value="",
        method="filter_portal",
        label=_("Source"),
        widget=BootstrapSelect,
    )
    document = django_filters.ModelChoiceFilter(
        queryset=Document.objects.all(),
        to_field_name="pk",
        method="filter_document",
        widget=forms.HiddenInput(),
    )
    user = django_filters.ModelChoiceFilter(
        queryset=User.objects.get_public_profiles(),
        to_field_name="username",
        method="filter_user",
        widget=forms.HiddenInput(),
    )
    number = django_filters.NumberFilter(
        method="filter_number", widget=forms.HiddenInput()
    )
    created_at = django_filters.DateFromToRangeFilter(
        method="filter_created_at",
        widget=DateRangeWidget,
    )

    class Meta:
        model = Page
        fields = [
            "q",
            "jurisdiction",
            "campaign",
            "tag",
            "publicbody",
            "collection",
            "number",
            "user",
            "portal",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get("request")
        if request is None:
            request = self.view.request
        self.request = request
        self.filters["foirequest"].queryset = get_read_foirequest_queryset(request)

        self.filters["portal"].extra["choices"] = [
            (p.pk, str(p)) for p in get_portal_queryset(request)
        ] + [("-", _("All"))]

    def has_query(self):
        return bool(self.request.GET.get("q"))

    def filter_queryset(self, queryset):
        required_unlisted_filters = {"document", "collection"}
        filter_present = any(
            v
            for k, v in self.form.cleaned_data.items()
            if k in required_unlisted_filters
        )
        if not filter_present:
            queryset = queryset.filter(listed=True)
        if not self.form.cleaned_data.get("portal"):
            queryset = self.apply_filter(queryset, "portal", portal=0)
            queryset = self.apply_filter(
                queryset,
                "foirequest",
                ESQ("bool", must={"exists": {"field": "foirequest"}}),
            )
        if not self.has_query():
            # Only show first page when there's no query
            queryset = self.apply_filter(queryset, "number", number=1)
        return super().filter_queryset(queryset)

    def filter_jurisdiction(self, qs, name, value):
        return self.apply_filter(qs, name, jurisdiction=value.id)

    def filter_campaign(self, qs, name, value):
        if value == "-":
            return qs.filter(ESQ("bool", must_not={"exists": {"field": "campaign"}}))
        return self.apply_filter(qs, name, campaign=value.id)

    def filter_tag(self, qs, name, value):
        return self.apply_filter(qs, name, tags=value.id)

    def filter_publicbody(self, qs, name, value):
        return self.apply_filter(qs, name, publicbody=value.id)

    def filter_foirequest(self, qs, name, value):
        return self.apply_filter(qs, name, foirequest=value.id)

    def filter_collection(self, qs, name, collection):
        if not collection.can_read(self.request):
            return qs.none()
        qs = self.apply_filter(qs, name, collections=collection.id)
        qs = self.apply_data_filters(qs, collection.settings.get("filters", []))
        return qs

    def filter_directory(self, qs, name, directory):
        if not directory.collection.can_read(self.request):
            return qs.none()
        qs = self.apply_filter(qs, name, directories=directory.id)
        return qs

    def filter_portal(self, qs, name, portal_value):
        if portal_value == "-":
            pass
        else:
            try:
                portal_qs = get_portal_queryset(self.request)
                portal = portal_qs.get(id=int(portal_value))
            except (DocumentPortal.DoesNotExist, IndexError):
                return qs.none()
            qs = self.apply_filter(qs, name, portal=portal.id)
            qs = self.apply_data_filters(qs, portal.settings.get("filters", []))

            if not self.has_query():
                qs = qs.add_sort()
                qs = qs.add_sort("-created_at")
        return qs

    def apply_data_filters(self, qs, filters):
        for filt in filters:
            es_key = filt["key"].replace("__", ".")
            if self.has_query() and filt.get("facet"):
                facet = filt.get("facet_config", {"type": "term"})
                if facet["type"] == "term":
                    qs = qs.add_aggregation([es_key])
                elif facet["type"] == "date_histogram":
                    facet_kwargs = {
                        k: v for k, v in facet.items() if k in ("interval", "format")
                    }
                    qs = qs.add_date_histogram(es_key, **facet_kwargs)

            if not filt["key"].startswith("data."):
                continue
            val = self.request.GET.get(filt["key"])
            if not val:
                continue
            data_type = filt.get("datatype")
            if data_type:
                try:
                    if data_type == "int":
                        val = int(val)
                except ValueError:
                    continue
            qs = qs.filter(**{es_key: val})
        return qs

    def filter_document(self, qs, name, value):
        if not value.can_read(self.request):
            return qs.none()
        return self.apply_filter(qs, name, document=value.id)

    def filter_user(self, qs, name, value):
        return self.apply_filter(qs, name, user=value.id)

    def filter_number(self, qs, name, value):
        return self.apply_filter(qs, name, number=int(value))

    def filter_created_at(self, qs, name, value):
        range_kwargs = {}
        if value.start is not None:
            range_kwargs["gte"] = value.start
        if value.stop is not None:
            range_kwargs["lte"] = value.stop

        return self.apply_filter(qs, name, ESQ("range", created_at=range_kwargs))
