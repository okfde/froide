import json
from collections import OrderedDict

from django.conf import settings
from django.utils.html import format_html

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer
from rest_framework.utils.serializer_helpers import ReturnDict
from rest_framework.decorators import action
from rest_framework.reverse import reverse
from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from rest_framework_jsonp.renderers import JSONPRenderer

from haystack.query import SearchQuerySet


def get_fake_api_context(url='/'):
    factory = APIRequestFactory()
    request = factory.get(url)

    return {
        'request': Request(request),
    }


class CustomLimitOffsetPagination(LimitOffsetPagination):
    max_limit = 50

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


class OpenRefineReconciliationMixin(object):
    class RECONCILIATION_META:
        name = None
        id = None
        model = None
        api_list = None
        obj_short_link = None
        filters = []
        properties = []
        properties_dict = {}

    def _reconciliation_meta(self, request):
        api_url = reverse(self.RECONCILIATION_META.api_list, request=request)

        detail_url = ''
        if self.RECONCILIATION_META.obj_short_link:
            magic = '13374223'
            detail_url = reverse(
                self.RECONCILIATION_META.obj_short_link,
                kwargs={'obj_id': magic}, request=request)
            detail_url = detail_url.replace(magic, '{{id}}')

        name = self.RECONCILIATION_META.name

        return Response({
            'name': "%s Reconciliation Service %s" % (
                settings.SITE_NAME,
                name
            ),
            'identifierSpace': api_url,
            'schemaSpace': api_url,
            'view': {
                'url': detail_url
            },
            'defaultTypes': [
                {
                    'id': self.RECONCILIATION_META.id,
                    'name': name
                }
            ],
            # 'suggest': {
            #     self.RECONCILIATION_META.id: {
            #         'service_path': 'reconciliation-suggest-service/',
            #         'service_url': api_url,
            #         'flyout_service_path': 'reconciliation-flyout/',
            #     }
            # },
            'extend': {
                'propose_properties': {
                    'service_url': api_url,
                    'service_path': 'reconciliation-propose-properties/'
                },
                'property_settings': []
            }
        })

    def _apply_openrefine_jsonp(self, request):
        if request.GET.get('callback'):
            # Force set JSONPRenderer
            request.accepted_renderer = JSONPRenderer()
        else:
            # Fore JSONRenderer because requests come with HTML in Accept header
            request.accepted_renderer = JSONRenderer()

    def _get_reconciliation_results(self, request, queries):
        result = {}
        for key in queries:
            query = queries[key]
            result[key] = {
                'result': list(self._get_reconciliation_result(query))
            }
        return result

    def _get_reconciliation_result(self, query):
        limit = min(query.get('limit', 3), 10)
        q = query.get('query')
        properties = query.get('properties', [])
        ALLOWED_FILTERS = set(self.RECONCILIATION_META.filters)
        queries = self.RECONCILIATION_META.properties_dict
        filters = {}
        for prop in properties:
            p = prop.get('p', prop.get('pid', None))
            if p not in ALLOWED_FILTERS:
                continue
            v = prop.get('v', None)
            if v is None:
                continue
            if isinstance(v, list):
                if not v:
                    continue
                v = v[0]
            query = queries[p].get('query', p)
            filters[query] = str(v)
        if not q:
            return
        return self._search_reconciliation_results(q, filters, limit)

    def _search_reconciliation_results(self, query, filters, limit):
        sqs = SearchQuerySet().models(self.RECONCILIATION_META.model)
        for key, val in filters.items():
            sqs = sqs.filter(**{key: val})
        sqs = sqs.auto_query(query)[:limit]
        for r in sqs:
            yield {
                'id': str(r.pk),
                'name': r.name,
                'type': [r.model_name],
                'score': r.score,
                'match': r.score >= 4  # FIXME: this is quite arbitrary
            }

    def _get_reconciliation_extend(self, request, query):
        """
        This implementation ignores settings
        """
        ids = query.get('ids', [])
        properties = query.get('properties', [])
        props = [
            p['id'] for p in properties
            if p.get('id') in self.RECONCILIATION_META.properties_dict
        ]
        qs = self.RECONCILIATION_META.model.objects.filter(id__in=ids)
        for prop in self.RECONCILIATION_META.properties:
            if prop['id'] in props and '__' in prop.get('query', ''):
                qs = qs.select_related(prop['query'].split('__')[0])

        meta = [{
            'id': self.RECONCILIATION_META.properties_dict[p]['id'],
            'name': self.RECONCILIATION_META.properties_dict[p]['name']
        } for p in props]
        objs = {str(o.id): o for o in qs}

        def make_prop(pk, objs, props):
            if pk not in objs:
                return {p: {} for p in props}
            obj = objs[pk]
            result = {}
            for p in props:
                meta = self.RECONCILIATION_META.properties_dict[p]
                item = meta.get('query', meta['id'])
                val = obj
                for key in item.split('__'):
                    val = getattr(val, key, None)
                    if val is None:
                        break
                if val is None:
                    val = {}
                else:
                    val = {'str': str(val)}
                result[p] = [val]
            return result

        rows = {
            id_: make_prop(id_, objs, props) for id_ in ids
        }

        return {
            'meta': meta,
            'rows': rows
        }

    @action(
        detail=False,
        methods=['get', 'post'],
        permission_classes=(),
        authentication_classes=(),
    )
    def reconciliation(self, request):
        '''
        This is a OpenRefine Reconciliation API endpoint
        https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API
        It's a bit messy.
        '''
        self._apply_openrefine_jsonp(request)
        if request.method == 'GET':
            return self._reconciliation_meta(request)

        methods = {
            'queries': self._get_reconciliation_results,
            'extend': self._get_reconciliation_extend
        }

        payload = None
        for kind in methods.keys():
            if request.POST.get(kind):
                payload = request.POST.get(kind)
                break

        if payload is None:
            return Response([])
        try:
            payload = json.loads(payload)
        except ValueError:
            return Response([])

        method = methods[kind]
        return Response(method(request, payload))

    @action(
        detail=False,
        methods=['get', 'post'],
        permission_classes=(),
        authentication_classes=(),
        url_path='reconciliation-propose-properties'
    )
    def reconciliation_propose_properties(self, request):
        """
        Implements OpenRefine Data Extension API
        https://github.com/OpenRefine/OpenRefine/wiki/Data-Extension-API

        """
        self._apply_openrefine_jsonp(request)

        properties = self.RECONCILIATION_META.properties
        limit = request.GET.get('limit', len(properties))

        return Response({
            'properties': properties[:limit],
            'type': self.RECONCILIATION_META.id,
            'limit': limit
        })

    @action(
        detail=False,
        methods=['get', 'post'],
        permission_classes=(),
        authentication_classes=(),
        url_path='reconciliation-flyout'
    )
    def reconciliation_flyout_entity(self, request):
        """
        Implements OpenRefine Flyout Entry Point
        https://github.com/OpenRefine/OpenRefine/wiki/Suggest-API#flyout-entry-point

        """
        self._apply_openrefine_jsonp(request)
        req_id = request.GET.get('id')
        if req_id is None:
            return Response({})
        model = self.RECONCILIATION_META.model
        try:
            obj = model.objects.get(pk=req_id)
        except model.DoesNotExist:
            return Response({})
        return Response({
            'id': str(obj.obj),
            'html': format_html('<p>{}</p>', obj)
        })

    @action(
        detail=False,
        methods=['get', 'post'],
        permission_classes=(),
        authentication_classes=(),
        url_path='reconciliation-suggest-service'
    )
    def reconciliation_suggest_service(self, request):
        """
        Implements OpenRefine Suggest Entry Point
        https://github.com/OpenRefine/OpenRefine/wiki/Suggest-API#suggest-entry-point

        Only implements prefix
        """
        self._apply_openrefine_jsonp(request)
        q = request.GET.get('prefix')
        response = {
            "code": "/api/status/ok",
            "status": "200 OK",
            "prefix": q or '',
            "result": []
        }
        if q is None:
            return Response(response)

        results = []
        for f in self.RECONCILIATION_META.filters:
            if f.startswith(q):
                results.append({
                    'id': f,
                    'name': f,
                })
        response['result'] = results

        return Response(response)
