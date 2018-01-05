from collections import OrderedDict

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer
from rest_framework.utils.serializer_helpers import ReturnDict


class CustomLimitOffsetPagination(LimitOffsetPagination):
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('meta', OrderedDict([
                ('limit', self.limit),
                ('next', self.get_next_link()),
                ('offset', self.offset),
                ('previous', self.get_previous_link()),
                ('total_count', self.count),
            ])),
            ('objects', data),
        ]))


class SearchFacetListSerializer(ListSerializer):
    @property
    def data(self):
        ret = super(ListSerializer, self).data
        return ReturnDict(ret, serializer=self)

    def to_representation(self, instance):
        ret = super(SearchFacetListSerializer, self).to_representation(instance)

        ret = OrderedDict([
            ('results', ret),
            ('facets', self._context.get('facets', {'fields': {}})),
        ])
        return ret
