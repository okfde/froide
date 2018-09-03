import json

from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.settings import api_settings

from rest_framework_jsonp.renderers import JSONPRenderer

from django_filters import rest_framework as filters

from froide.helper.api_utils import OpenRefineReconciliationMixin

from .models import GeoRegion


class GeoRegionSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name='api:georegion-detail',
        lookup_field='pk'
    )
    part_of = serializers.HyperlinkedRelatedField(
        view_name='api:georegion-detail',
        lookup_field='pk',
        read_only=True,
        many=False
    )
    geom = serializers.SerializerMethodField()
    gov_seat = serializers.SerializerMethodField()
    centroid = serializers.SerializerMethodField()

    class Meta:
        model = GeoRegion
        depth = 0
        fields = (
            'resource_uri', 'id', 'name', 'slug', 'kind',
            'kind_detail', 'level',
            'region_identifier', 'global_identifier',
            'area', 'population', 'valid_on',
            'geom', 'gov_seat',
            'centroid',
            'part_of',
        )

    def get_geom(self, obj):
        if obj.geom is not None:
            return json.loads(obj.geom.json)
        return None

    def get_gov_seat(self, obj):
        if obj.gov_seat is not None:
            return json.loads(obj.gov_seat.json)
        return None

    def get_centroid(self, obj):
        if obj.geom is not None:
            return json.loads(obj.geom.centroid.json)
        return None


class GeoRegionFilter(filters.FilterSet):
    q = filters.CharFilter(method='search_filter')
    kind = filters.CharFilter(method='kind_filter')
    level = filters.NumberFilter(method='level_filter')

    class Meta:
        model = GeoRegion
        fields = (
            'name', 'level', 'kind', 'slug'
        )

    def search_filter(self, queryset, name, value):
        return queryset.filter(name__icontains=value)

    def kind_filter(self, queryset, name, value):
        return queryset.filter(kind=value)

    def level_filter(self, queryset, name, value):
        return queryset.filter(level=value)


class GeoRegionViewSet(OpenRefineReconciliationMixin,
                       viewsets.ReadOnlyModelViewSet):
    serializer_class = GeoRegionSerializer
    queryset = GeoRegion.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = GeoRegionFilter

    # OpenRefine needs JSONP responses
    # This is OK because authentication is not considered
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (JSONPRenderer,)

    class RECONCILIATION_META:
        name = 'GeoRegion'
        id = 'georegion'
        model = GeoRegion
        api_list = 'api:georegion-list'
        obj_short_link = None
        filters = ['kind', 'level']
        properties = [{
            'id': 'population',
            'name': 'population',
            }, {
            'id': 'area',
            'name': 'area',
            }, {
            'id': 'geom',
            'name': 'geom',
            }, {
            'id': 'name',
            'name': 'Name'
            }, {
            'id': 'id',
            'name': 'ID'
            }, {
            'id': 'slug',
            'name': 'Slug'
            }, {
            'id': 'kind',
            'name': 'Kind'
        }]
        properties_dict = {
            p['id']: p for p in properties
        }

    def _search_reconciliation_results(self, query, filters, limit):
        qs = GeoRegion.objects.all()
        for key, val in filters.items():
            qs = qs.filter(**{key: val})
        qs = qs.filter(name__contains=query)[:limit]
        for r in qs:
            yield {
                'id': str(r.pk),
                'name': r.name,
                'type': ['georegion'],
                'score': 4,
                'match': True  # FIXME: this is quite arbitrary
            }
