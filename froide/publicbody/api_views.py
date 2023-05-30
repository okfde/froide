import json

from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils import translation

from django_filters import rest_framework as filters
from elasticsearch_dsl.query import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.settings import api_settings
from rest_framework_jsonp.renderers import JSONPRenderer

from froide.georegion.models import GeoRegion
from froide.helper.api_utils import (
    OpenRefineReconciliationMixin,
    SearchFacetListSerializer,
)
from froide.helper.search import SearchQuerySetWrapper
from froide.helper.search.api_views import ESQueryMixin

from .documents import PublicBodyDocument
from .models import Category, Classification, FoiLaw, Jurisdiction, PublicBody


def get_language_from_query(request):
    if request:
        lang = request.GET.get("language", settings.LANGUAGE_CODE)
        lang_dict = dict(settings.LANGUAGES)
        if lang in lang_dict:
            return lang
    return settings.LANGUAGE_CODE


class JurisdictionSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:jurisdiction-detail", lookup_field="pk"
    )
    region = serializers.HyperlinkedRelatedField(
        view_name="api:georegion-detail", lookup_field="pk", read_only=True
    )
    site_url = serializers.CharField(source="get_absolute_domain_url")

    class Meta:
        model = Jurisdiction
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "name",
            "rank",
            "description",
            "slug",
            "site_url",
            "region",
        )


class JurisdictionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JurisdictionSerializer
    queryset = Jurisdiction.objects.all()


class SimpleFoiLawSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:law-detail", lookup_field="pk"
    )
    jurisdiction = serializers.HyperlinkedRelatedField(
        view_name="api:jurisdiction-detail", lookup_field="pk", read_only=True
    )
    mediator = serializers.HyperlinkedRelatedField(
        view_name="api:publicbody-detail", lookup_field="pk", read_only=True
    )
    site_url = serializers.SerializerMethodField()

    class Meta:
        model = FoiLaw
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "name",
            "slug",
            "description",
            "long_description",
            "law_type",
            "created",
            "updated",
            "request_note",
            "request_note_html",
            "meta",
            "site_url",
            "jurisdiction",
            "email_only",
            "mediator",
            "priority",
            "url",
            "max_response_time",
            "email_only",
            "requires_signature",
            "max_response_time_unit",
            "letter_start",
            "letter_end",
        )

    def get_site_url(self, obj):
        language = get_language_from_query(self.context.get("request"))
        with translation.override(language):
            return obj.get_absolute_domain_url()

    def to_representation(self, instance):
        """Activate language based on request query param."""
        language = get_language_from_query(self.context.get("request"))
        instance.set_current_language(language)
        ret = super().to_representation(instance)
        return ret


class FoiLawSerializer(SimpleFoiLawSerializer):
    combined = serializers.HyperlinkedRelatedField(
        view_name="api:law-detail", lookup_field="pk", read_only=True, many=True
    )

    class Meta(SimpleFoiLawSerializer.Meta):
        fields = SimpleFoiLawSerializer.Meta.fields + (
            "refusal_reasons",
            "combined",
        )


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

    def search_filter(self, queryset, name, value):
        return queryset.filter(translations__name__icontains=value)


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


class TreeMixin(object):
    def get_parent(self, obj):
        return obj.get_parent()

    def get_children(self, obj):
        return obj.get_children()


class SimpleClassificationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Classification
        fields = (
            "id",
            "name",
            "slug",
            "depth",
        )


class ClassificationSerializer(SimpleClassificationSerializer):
    parent = serializers.HyperlinkedRelatedField(
        source="get_parent", read_only=True, view_name="api:classification-detail"
    )
    children = serializers.HyperlinkedRelatedField(
        source="get_children",
        many=True,
        read_only=True,
        view_name="api:classification-detail",
    )

    class Meta(SimpleClassificationSerializer.Meta):
        fields = SimpleClassificationSerializer.Meta.fields + ("parent", "children")


class SearchFilterMixin(object):
    def search_filter(self, queryset, name, value):
        return queryset.filter(name__icontains=value)


class TreeFilterMixin(object):
    def parent_filter(self, queryset, name, value):
        return queryset.intersection(value.get_children())

    def ancestor_filter(self, queryset, name, value):
        return queryset.intersection(value.get_descendants())


class ClassificationFilter(SearchFilterMixin, TreeFilterMixin, filters.FilterSet):
    q = filters.CharFilter(method="search_filter")
    parent = filters.ModelChoiceFilter(
        method="parent_filter", queryset=Classification.objects.all()
    )
    ancestor = filters.ModelChoiceFilter(
        method="ancestor_filter", queryset=Classification.objects.all()
    )

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


class SimpleCategorySerializer(TreeMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "is_topic",
            "depth",
        )


class CategorySerializer(SimpleCategorySerializer):
    parent = serializers.HyperlinkedRelatedField(
        source="get_parent", read_only=True, view_name="api:category-detail"
    )
    children = serializers.HyperlinkedRelatedField(
        source="get_children",
        many=True,
        read_only=True,
        view_name="api:category-detail",
    )

    class Meta(SimpleCategorySerializer.Meta):
        fields = SimpleCategorySerializer.Meta.fields + ("parent", "children")


class CategoryFilter(SearchFilterMixin, TreeFilterMixin, filters.FilterSet):
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


class SimplePublicBodySerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:publicbody-detail", lookup_field="pk"
    )
    id = serializers.IntegerField(source="pk")
    jurisdiction = serializers.HyperlinkedRelatedField(
        view_name="api:jurisdiction-detail",
        read_only=True,
    )
    classification = serializers.HyperlinkedRelatedField(
        view_name="api:classification-detail", read_only=True
    )

    site_url = serializers.CharField(source="get_absolute_domain_url")
    geo = serializers.SerializerMethodField()

    class Meta:
        model = PublicBody
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "name",
            "slug",
            "other_names",
            "description",
            "url",
            "depth",
            "classification",
            "email",
            "contact",
            "address",
            "fax",
            "request_note",
            "number_of_requests",
            "site_url",
            "jurisdiction",
            "request_note_html",
            "geo",
        )

    def get_geo(self, obj):
        if obj.geo is not None:
            return json.loads(obj.geo.json)
        return None


class PublicBodyListSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:publicbody-detail", lookup_field="pk"
    )
    root = serializers.HyperlinkedRelatedField(
        view_name="api:publicbody-detail", read_only=True
    )
    parent = serializers.HyperlinkedRelatedField(
        view_name="api:publicbody-detail", read_only=True
    )

    id = serializers.IntegerField(source="pk")
    jurisdiction = JurisdictionSerializer(read_only=True)
    laws = serializers.HyperlinkedRelatedField(
        view_name="api:law-detail", many=True, read_only=True
    )
    categories = SimpleCategorySerializer(read_only=True, many=True)
    classification = SimpleClassificationSerializer(read_only=True)
    regions = serializers.HyperlinkedRelatedField(
        view_name="api:georegion-detail", read_only=True, many=True
    )

    site_url = serializers.CharField(source="get_absolute_domain_url")
    geo = serializers.SerializerMethodField()

    class Meta:
        model = PublicBody
        list_serializer_class = SearchFacetListSerializer
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "name",
            "slug",
            "other_names",
            "description",
            "url",
            "parent",
            "root",
            "depth",
            "classification",
            "categories",
            "email",
            "contact",
            "address",
            "fax",
            "request_note",
            "number_of_requests",
            "site_url",
            "request_note_html",
            "jurisdiction",
            "laws",
            "regions",
            "source_reference",
            "alternative_emails",
            "wikidata_item",
            "extra_data",
            "geo",
        )

    def get_geo(self, obj):
        if obj.geo is not None:
            return json.loads(obj.geo.json)
        return None


class PublicBodySerializer(PublicBodyListSerializer):
    laws = FoiLawSerializer(many=True, read_only=True)


class PublicBodyFilter(SearchFilterMixin, filters.FilterSet):
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
                Q("multi_match", query=query, fields=["name_auto", "content"])
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
