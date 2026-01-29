from django.conf import settings
from django.contrib.gis.geos import Point
from django.db.models import Q

from django_filters import rest_framework as filters
from elasticsearch_dsl.query import Q as ESQ
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.settings import api_settings
from rest_framework_jsonp.renderers import JSONPRenderer

from froide.georegion.models import GeoRegion
from froide.helper.api_utils import (
    OpenRefineReconciliationMixin,
)
from froide.helper.search import SearchQuerySetWrapper
from froide.helper.search.api_views import ESQueryMixin

from .documents import PublicBodyDocument
from .models import Category, Classification, FoiLaw, Jurisdiction, PublicBody
from .serializers import (
    CategorySerializer,
    ClassificationSerializer,
    FoiLawSerializer,
    JurisdictionSerializer,
    PublicBodyListSerializer,
    PublicBodySerializer,
)


def make_search_filter(field):
    def search_filter(self, queryset, name, value):
        return queryset.filter(
            Q.create(
                [("{}__icontains".format(field), bit) for bit in value.split()],
                connector=Q.AND,
            )
        )

    return search_filter


class JurisdictionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JurisdictionSerializer
    queryset = Jurisdiction.objects.all().prefetch_related("region")


class FoiLawFilter(filters.FilterSet):
    id = filters.CharFilter(method="id_filter")
    q = filters.CharFilter(method="search_filter")
    meta = filters.BooleanFilter()

    class Meta:
        model = FoiLaw
        fields = ("jurisdiction", "mediator", "id")

    def id_filter(self, queryset, name, value):
        ids = value.split(",")
        try:
            ids = [int(i) for i in ids]
        except ValueError:
            return queryset
        return queryset.filter(pk__in=ids)

    search_filter = make_search_filter("translations__name")


class FoiLawViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FoiLawSerializer
    queryset = FoiLaw.objects.all()
    filterset_class = FoiLawFilter

    def get_queryset(self):
        lang = self.request.GET.get("language", settings.LANGUAGE_CODE)
        qs = FoiLaw.objects.language(lang)
        return self.optimize_query(qs)

    def optimize_query(self, qs):
        return qs.select_related(
            "jurisdiction",
            "mediator",
        ).prefetch_related("combined", "translations")

    @action(
        detail=False, methods=["get"], url_path="autocomplete", url_name="autocomplete"
    )
    def autocomplete(self, request):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        return self.get_paginated_response(
            [
                {
                    "value": x.pk,
                    "label": str(x.name),
                }
                for x in page
            ]
        )


class TreeFilterMixin(object):
    def parent_filter(self, queryset, name, value):
        return queryset.intersection(value.get_children())

    def ancestor_filter(self, queryset, name, value):
        return queryset.intersection(value.get_descendants())


class ClassificationFilter(TreeFilterMixin, filters.FilterSet):
    q = filters.CharFilter(method="search_filter")
    parent = filters.ModelChoiceFilter(
        method="parent_filter", queryset=Classification.objects.all()
    )
    ancestor = filters.ModelChoiceFilter(
        method="ancestor_filter", queryset=Classification.objects.all()
    )

    search_filter = make_search_filter("name")

    class Meta:
        model = Classification
        fields = (
            "name",
            "depth",
        )


class ClassificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClassificationSerializer
    queryset = Classification.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ClassificationFilter


class CategoryFilter(TreeFilterMixin, filters.FilterSet):
    q = filters.CharFilter(method="search_filter")
    parent = filters.ModelChoiceFilter(
        method="parent_filter", queryset=Category.objects.all()
    )
    ancestor = filters.ModelChoiceFilter(
        method="ancestor_filter", queryset=Category.objects.all()
    )

    class Meta:
        model = Category
        fields = (
            "name",
            "is_topic",
            "depth",
        )

    search_filter = make_search_filter("name")


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = CategoryFilter

    @action(
        detail=False, methods=["get"], url_path="autocomplete", url_name="autocomplete"
    )
    def autocomplete(self, request):
        page = self.paginate_queryset(
            self.filter_queryset(self.get_queryset()).only("name").order_by("name")
        )
        return self.get_paginated_response(
            [{"value": t.name, "label": t.name} for t in page]
        )


class PublicBodyFilter(filters.FilterSet):
    q = filters.CharFilter(method="search_filter")
    classification = filters.ModelChoiceFilter(
        method="classification_filter", queryset=Classification.objects.all()
    )
    category = filters.ModelMultipleChoiceFilter(
        method="category_filter", queryset=Category.objects.all()
    )
    regions = filters.CharFilter(method="regions_filter")
    lnglat = filters.CharFilter(method="lnglat_filter")

    class Meta:
        model = PublicBody
        fields = (
            "jurisdiction",
            "slug",
            "classification_id",
        )

    search_filter = make_search_filter("name")

    def classification_filter(self, queryset, name, value):
        tree_list = Classification.get_tree(parent=value)
        return queryset.filter(classification__in=tree_list)

    def category_filter(self, queryset, name, value):
        for v in value:
            queryset = queryset.filter(
                categories__in=Category.get_tree(parent=v)
            ).distinct()
        return queryset

    def regions_filter(self, queryset, name, value):
        if "," in value:
            ids = value.split(",")
        else:
            try:
                region = GeoRegion.objects.get(id=value)
                ids = GeoRegion.get_tree(parent=region)
            except GeoRegion.DoesNotExist:
                return queryset
        return queryset.filter(regions__in=ids)

    def lnglat_filter(self, queryset, name, value):
        if "," not in value:
            return queryset
        try:
            lnglat = value.split(",", 1)
            lnglat = (float(lnglat[0]), float(lnglat[1]))
        except (IndexError, ValueError):
            return queryset
        point = Point(lnglat[0], lnglat[1])
        return queryset.filter(regions__geom__covers=point)


class PublicBodyViewSet(
    OpenRefineReconciliationMixin, ESQueryMixin, viewsets.ReadOnlyModelViewSet
):
    serializer_action_classes = {
        "list": PublicBodyListSerializer,
        "retrieve": PublicBodySerializer,
    }
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PublicBodyFilter

    # OpenRefine needs JSONP responses
    # This is OK because authentication is not considered
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (JSONPRenderer,)

    class RECONCILIATION_META:
        name = "Public Body"
        id = "publicbody"
        model = PublicBody
        document = PublicBodyDocument
        api_list = "api:publicbody-list"
        obj_short_link = "publicbody-publicbody_shortlink"
        query_fields = ["name", "content"]
        filters = ["jurisdiction", "classification"]
        properties = [
            {
                "id": "classification",
                "name": "Classification",
                "query": "classification",
            },
            {"id": "jurisdiction", "name": "Jurisdiction", "query": "jurisdiction"},
            {"id": "email", "name": "Email"},
            {"id": "id", "name": "ID"},
            {"id": "slug", "name": "Slug"},
            {"id": "url", "name": "URL"},
            {"id": "fax", "name": "Fax"},
        ]
        properties_dict = {p["id"]: p for p in properties}

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return PublicBodyListSerializer

    def get_queryset(self):
        return self.optimize_query(PublicBody.objects.all())

    def optimize_query(self, qs):
        return qs.select_related("classification", "jurisdiction").prefetch_related(
            "categories",
            "laws",
            "regions",
        )

    @action(detail=False, methods=["get"])
    def search(self, request):
        return self.search_view(request)

    @action(
        detail=False, methods=["get"], url_path="autocomplete", url_name="autocomplete"
    )
    def autocomplete(self, request):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        return self.get_paginated_response(
            [{"value": t.id, "label": t.name} for t in page]
        )

    def get_serializer_context(self):
        ctx = super(PublicBodyViewSet, self).get_serializer_context()
        if self.action == "search":
            if hasattr(self, "sqs"):
                ctx["facets"] = self.sqs.get_aggregations()
        return ctx

    def get_searchqueryset(self):
        query = self.request.GET.get("q", "")

        sqs = SearchQuerySetWrapper(PublicBodyDocument.search(), PublicBody)

        if len(query) > 2:
            sqs = sqs.set_query(
                ESQ("multi_match", query=query, fields=["name_auto", "content"])
            )

        model_filters = {
            "jurisdiction": Jurisdiction,
            "classification": Classification,
            "categories": Category,
            "regions": GeoRegion,
        }
        for key, model in model_filters.items():
            pks = self.request.GET.getlist(key)
            if pks:
                try:
                    obj = model.objects.filter(pk__in=pks)
                    sqs = sqs.filter(**{key: [o.pk for o in obj]})
                except ValueError:
                    # Make result set empty, no 0 pk present
                    sqs = sqs.filter(key, **{key: 0})

        other_filters = {"regions_kind": "regions_kind"}
        for key, search_key in other_filters.items():
            values = self.request.GET.getlist(key)
            if values:
                sqs = sqs.filter(**{search_key: values})

        sqs = sqs.add_aggregation(
            [
                "jurisdiction",
                "classification",
                "categories",
                "regions",
            ]
        )
        return sqs
