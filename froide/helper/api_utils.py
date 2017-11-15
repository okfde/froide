from collections import OrderedDict

from tastypie.authentication import (MultiAuthentication,
    BasicAuthentication, SessionAuthentication)
from tastypie.authorization import ReadOnlyAuthorization

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class AnonymousGetAuthentication(BasicAuthentication):
    def is_authenticated(self, request, **kwargs):
        if request.method == 'GET':
            return True
        multi_auth = MultiAuthentication(SessionAuthentication(),
            BasicAuthentication())
        return multi_auth.is_authenticated(request, **kwargs)


class CustomDjangoAuthorization(ReadOnlyAuthorization):
    pass


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
            ('objects', data)
        ]))
