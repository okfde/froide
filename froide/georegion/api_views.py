import json
import re

from django.contrib.gis.geos import Point
from django.db.models import Q

from django_filters import rest_framework as filters
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.settings import api_settings
from rest_framework_jsonp.renderers import JSONPRenderer

from froide.helper.api_utils import OpenRefineReconciliationMixin

from .models import GeoRegion

GERMAN_PLZ_RE = re.compile(r"\d{5}")


class GeoRegionSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:georegion-detail", lookup_field="pk"
    )
    part_of = serializers.HyperlinkedRelatedField(
        view_name="api:georegion-detail", lookup_field="pk", read_only=True, many=False
    )
    centroid = serializers.SerializerMethodField()

    class Meta:
        model = GeoRegion
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "name",
            "slug",
            "kind",
            "kind_detail",
            "level",
            "region_identifier",
            "global_identifier",
            "area",
            "population",
            "valid_on",
            "part_of",
            "centroid",
        )

    def get_centroid(self, obj):
        if obj.geom is not None:
            return json.loads(obj.geom.centroid.json)
        return None


class GeoRegionDetailSerializer(GeoRegionSerializer):
    geom = serializers.SerializerMethodField()
    gov_seat = serializers.SerializerMethodField()

    class Meta(GeoRegionSerializer.Meta):
        fields = GeoRegionSerializer.Meta.fields + (
            "geom",
            "gov_seat",
            "centroid",
        )

    def get_geom(self, obj):
        if obj.geom is not None:
            return json.loads(obj.geom.json)
        return None

    def get_gov_seat(self, obj):
        if obj.gov_seat is not None:
            return json.loads(obj.gov_seat.json)
        return None


class GeoRegionFilter(filters.FilterSet):
    id = filters.CharFilter(method="id_filter")
    q = filters.CharFilter(method="search_filter")
    kind = filters.CharFilter(method="kind_filter")
    level = filters.NumberFilter(method="level_filter")
    ancestor = filters.ModelChoiceFilter(
        method="ancestor_filter", queryset=GeoRegion.objects.all()
    )
    latlng = filters.CharFilter(method="latlng_filter")
    name = filters.CharFilter(method="name_filter")
    kind_detail = filters.CharFilter(method="kind_detail_filter")
    region_identifier = filters.CharFilter(method="region_identifier_filter")

    class Meta:
        model = GeoRegion
        fields = ("name", "level", "kind", "slug")

    def name_filter(self, queryset, name, value):
        qs = queryset.filter(name=value)
        if not qs:
            return queryset.filter(name=value.capitalize())
        return qs

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(region_identifier__startswith=value)
        )

    def kind_filter(self, queryset, name, value):
        return queryset.filter(kind__in=value.split(","))

    def level_filter(self, queryset, name, value):
        return queryset.filter(level=value)

    def id_filter(self, queryset, name, value):
        ids = value.split(",")
        try:
            return queryset.filter(pk__in=ids)
        except ValueError:
            return queryset

    def ancestor_filter(self, queryset, name, value):
        descendants = value.get_descendants()
        return queryset.filter(id__in=descendants)

    def region_identifier_filter(self, queryset, name, value):
        return queryset.filter(region_identifier=value)

    def kind_detail_filter(self, queryset, name, value):
        return queryset.filter(kind_detail=value)

    def latlng_filter(self, queryset, name, value):
        try:
            parts = value.split(",", 1)
            lat, lng = float(parts[0]), float(parts[1])
            return queryset.filter(geom__covers=Point(lng, lat))
        except (ValueError, IndexError):
            pass
        return queryset


class GeoRegionViewSet(OpenRefineReconciliationMixin, viewsets.ReadOnlyModelViewSet):
    serializer_action_classes = {
        "list": GeoRegionSerializer,
        "retrieve": GeoRegionDetailSerializer,
    }
    queryset = GeoRegion.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = GeoRegionFilter

    # OpenRefine needs JSONP responses
    # This is OK because authentication is not considered
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (JSONPRenderer,)

    class RECONCILIATION_META:
        name = "GeoRegion"
        id = "georegion"
        model = GeoRegion
        api_list = "api:georegion-list"
        obj_short_link = None
        filters = ["kind", "level"]
        properties = [
            {
                "id": "population",
                "name": "population",
            },
            {
                "id": "area",
                "name": "area",
            },
            {
                "id": "geom",
                "name": "geom",
            },
            {"id": "name", "name": "Name"},
            {"id": "id", "name": "ID"},
            {"id": "slug", "name": "Slug"},
            {"id": "kind", "name": "Kind"},
            {"id": "region_identifier", "name": "Region identifier"},
            {"id": "global_identifier", "name": "Global identifier"},
        ]
        properties_dict = {p["id"]: p for p in properties}

    def get_serializer_class(self):
        try:
            # request is not available when called from manage.py generateschema
            if self.request and self.request.user.is_superuser:
                return GeoRegionDetailSerializer
            return self.serializer_action_classes[self.action]
        except KeyError:
            return GeoRegionSerializer

    def _search_reconciliation_results(self, query, filters, limit):
        qs = GeoRegion.objects.all()
        for key, val in filters.items():
            qs = qs.filter(**{key: val})
        # FIXME: Special German case
        match = GERMAN_PLZ_RE.match(query)
        zip_region = None
        if match:
            try:
                zip_region = GeoRegion.objects.get(name=query, kind="zipcode")
                qs = qs.filter(geom__covers=zip_region.geom.centroid)
            except GeoRegion.DoesNotExist:
                pass

        if not match or not zip_region:
            qs = qs.filter(name__contains=query)[:limit]

        for r in qs:
            yield {
                "id": str(r.pk),
                "name": r.name,
                "type": ["georegion"],
                "score": 4,
                "match": True,  # FIXME: this is quite arbitrary
            }

    @action(
        detail=False, methods=["get"], url_path="autocomplete", url_name="autocomplete"
    )
    def autocomplete(self, request):
        page = self.paginate_queryset(
            self.filter_queryset(self.get_queryset())
            .only("id", "name", "kind", "kind_detail", "region_identifier")
            .order_by("level", "name")
        )
        return self.get_paginated_response(
            [
                {
                    "value": x.pk,
                    "label": str(x),
                }
                for x in page
            ]
        )
