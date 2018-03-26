import json

from django.conf import settings

from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.decorators import list_route
from rest_framework.renderers import JSONRenderer

from rest_framework_jsonp.renderers import JSONPRenderer

from django_filters import rest_framework as filters

from haystack.query import SearchQuerySet
from haystack.inputs import AutoQuery

from froide.helper.api_utils import SearchFacetListSerializer
from froide.helper.search import SearchQuerySetWrapper

from .models import (PublicBody, Category, Jurisdiction, FoiLaw,
                     Classification)


class JurisdictionSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name='api:jurisdiction-detail',
        lookup_field='pk'
    )
    site_url = serializers.CharField(source='get_absolute_domain_url')

    class Meta:
        model = Jurisdiction
        depth = 0
        fields = (
            'resource_uri', 'id', 'name', 'rank', 'description', 'slug',
            'site_url'
        )


class JurisdictionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JurisdictionSerializer
    queryset = Jurisdiction.objects.all()


class FoiLawSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name='api:law-detail',
        lookup_field='pk'
    )
    jurisdiction = serializers.HyperlinkedRelatedField(
        view_name='api:jurisdiction-detail',
        lookup_field='pk',
        read_only=True
    )
    mediator = serializers.HyperlinkedRelatedField(
        view_name='api:publicbody-detail',
        lookup_field='pk',
        read_only=True
    )
    combined = serializers.HyperlinkedRelatedField(
        view_name='api:law-detail',
        lookup_field='pk',
        read_only=True,
        many=True
    )
    site_url = serializers.CharField(source='get_absolute_domain_url')

    class Meta:
        model = FoiLaw
        depth = 0
        fields = (
            'resource_uri', 'id', 'name', 'slug', 'description', 'long_description',
            'created', 'updated', 'request_note', 'request_note_html', 'meta',
            'combined', 'letter_start', 'letter_end', 'jurisdiction',
            'priority', 'url', 'max_response_time', 'site_url',
            'max_response_time_unit', 'refusal_reasons', 'mediator'
        )


class FoiLawViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FoiLawSerializer
    queryset = FoiLaw.objects.all()


class TreeMixin(object):
    def get_parent(self, obj):
        return obj.get_parent()

    def get_children(self, obj):
        return obj.get_children()


class ClassificationSerializer(serializers.HyperlinkedModelSerializer):
    parent = serializers.HyperlinkedRelatedField(
        source='get_parent', read_only=True,
        view_name='api:classification-detail'
    )
    children = serializers.HyperlinkedRelatedField(
        source='get_children', many=True, read_only=True,
        view_name='api:classification-detail'
    )

    class Meta:
        model = Classification
        fields = (
            'id', 'name', 'slug', 'depth',
            'parent', 'children'
        )


class SearchFilterMixin(object):
    def search_filter(self, queryset, name, value):
        return queryset.filter(name__icontains=value)


class TreeFilterMixin(object):
    def parent_filter(self, queryset, name, value):
        return queryset.intersection(value.get_children())

    def ancestor_filter(self, queryset, name, value):
        return queryset.intersection(value.get_descendants())


class ClassificationFilter(SearchFilterMixin, TreeFilterMixin,
                           filters.FilterSet):
    q = filters.CharFilter(method='search_filter')
    parent = filters.ModelChoiceFilter(method='parent_filter',
        queryset=Classification.objects.all())
    ancestor = filters.ModelChoiceFilter(method='ancestor_filter',
        queryset=Classification.objects.all())

    class Meta:
        model = Classification
        fields = (
            'name', 'depth',
        )


class ClassificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClassificationSerializer
    queryset = Classification.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = ClassificationFilter


class CategorySerializer(TreeMixin, serializers.HyperlinkedModelSerializer):
    parent = serializers.HyperlinkedRelatedField(
        source='get_parent', read_only=True,
        view_name='api:category-detail'
    )
    children = serializers.HyperlinkedRelatedField(
        source='get_children', many=True, read_only=True,
        view_name='api:category-detail'
    )

    class Meta:
        model = Category
        fields = (
            'id', 'name', 'slug', 'is_topic', 'depth',
            'parent', 'children'
        )


class CategoryFilter(SearchFilterMixin, TreeFilterMixin, filters.FilterSet):
    q = filters.CharFilter(method='search_filter')
    parent = filters.ModelChoiceFilter(method='parent_filter',
        queryset=Category.objects.all())
    ancestor = filters.ModelChoiceFilter(method='ancestor_filter',
        queryset=Category.objects.all())

    class Meta:
        model = Category
        fields = (
            'name', 'is_topic', 'depth',
        )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = CategoryFilter

    @list_route(methods=['get'], url_path='autocomplete',
                url_name='autocomplete')
    def autocomplete(self, request):
        query = request.GET.get('query', '')
        tags = []
        if query:
            tags = Category.objects.filter(name__istartswith=query)
            tags = [t for t in tags.values_list('name', flat=True)]
        return Response(tags)


class PublicBodySerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name='api:publicbody-detail',
        lookup_field='pk'
    )
    root = serializers.HyperlinkedRelatedField(
        view_name='api:publicbody-detail',
        lookup_field='pk',
        read_only=True
    )
    parent = serializers.HyperlinkedRelatedField(
        view_name='api:publicbody-detail',
        lookup_field='pk',
        read_only=True
    )

    id = serializers.IntegerField(source='pk')
    jurisdiction = JurisdictionSerializer(read_only=True)
    default_law = FoiLawSerializer(read_only=True)
    laws = serializers.HyperlinkedRelatedField(
        view_name='api:law-detail',
        lookup_field='pk',
        many=True,
        read_only=True
    )
    categories = CategorySerializer(read_only=True, many=True)
    classification = ClassificationSerializer(read_only=True)

    site_url = serializers.CharField(source='get_absolute_domain_url')

    class Meta:
        model = PublicBody
        list_serializer_class = SearchFacetListSerializer
        depth = 0
        fields = (
            'resource_uri', 'id', 'name', 'slug', 'other_names',
            'description', 'url', 'parent', 'root',
            'depth', 'classification', 'categories',
            'email', 'contact', 'address',
            'request_note', 'number_of_requests',
            'laws', 'site_url',
            'jurisdiction', 'request_note_html',
            'default_law',
        )


class PublicBodyFilter(SearchFilterMixin, filters.FilterSet):
    q = filters.CharFilter(method='search_filter')
    classification = filters.ModelChoiceFilter(method='classification_filter',
        queryset=Classification.objects.all())
    category = filters.ModelMultipleChoiceFilter(method='category_filter',
        queryset=Category.objects.all())

    class Meta:
        model = PublicBody
        fields = (
            'jurisdiction', 'slug', 'classification_id',
        )

    def classification_filter(self, queryset, name, value):
        tree_list = Classification.get_tree(parent=value)
        return queryset.filter(classification__in=tree_list)

    def category_filter(self, queryset, name, value):
        for v in value:
            queryset = queryset.filter(
                categories__in=Category.get_tree(parent=v)
            )
        return queryset


class PublicBodyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PublicBodySerializer
    queryset = PublicBody.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = PublicBodyFilter

    REFINE_PROPOSE_PROPERTIES = [{
        'id': 'classification',
        'name': 'Classification',
        'query': 'classification__name'
        }, {
        'id': 'jurisdiction',
        'name': 'Jurisdiction',
        'query': 'jurisdiction__name'
        }, {
        'id': 'email',
        'name': 'Email'
        }, {
        'id': 'id',
        'name': 'ID'
        }, {
        'id': 'slug',
        'name': 'Slug'
        }, {
        'id': 'url',
        'name': 'URL'
    }]
    REFINE_PROPOSE_PROPERTIES_DICT = {
        p['id']: p for p in REFINE_PROPOSE_PROPERTIES
    }

    @list_route(methods=['get'])
    def search(self, request):
        self.queryset = self.get_searchqueryset(request)

        page = self.paginate_queryset(self.queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
        else:
            serializer = self.get_serializer(self.queryset, many=True)

        data = serializer.data

        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)

    @list_route(
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

    def _reconciliation_meta(self, request):
        pb_api_url = reverse('api:publicbody-list', request=request)
        magic = '13374223'
        pb_detail_url = reverse('publicbody-publicbody_shortlink', kwargs={
            'obj_id': magic
        }, request=request)
        pb_detail_url = pb_detail_url.replace(magic, '{{id}}')

        return Response({
            'name': "%s Reconciliation Service" % settings.SITE_NAME,
            'identifierSpace': pb_api_url,
            'schemaSpace': pb_api_url,
            'view': {
                'url': pb_detail_url
            },
            'defaultTypes': [
                {
                    'id': 'publicbody',
                    'name': 'Public Body',
                }
            ],
            'extend': {
                'propose_properties': {
                    'service_url': pb_api_url,
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
        ALLOWED_PROPERTIES = set(['jurisdiction'])
        filters = {}
        for prop in properties:
            if prop.get('p', None) in ALLOWED_PROPERTIES:
                v = prop.get('v', None)
                if v is None:
                    continue
                if isinstance(v, list):
                    if not v:
                        continue
                    v = v[0]
                filters[prop['p']] = str(v)
        if not q:
            return
        sqs = SearchQuerySet().models(PublicBody)
        for key, val in filters.items():
            sqs = sqs.filter(**{key: val})
        sqs = sqs.auto_query(q)[:limit]
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
            if p.get('id') in self.REFINE_PROPOSE_PROPERTIES_DICT
        ]
        qs = PublicBody.objects.filter(id__in=ids)
        for prop in self.REFINE_PROPOSE_PROPERTIES:
            if prop['id'] in props and '__' in prop.get('query', ''):
                qs = qs.select_related(prop['query'].split('__')[0])

        meta = [{
            'id': self.REFINE_PROPOSE_PROPERTIES_DICT[p]['id'],
            'name': self.REFINE_PROPOSE_PROPERTIES_DICT[p]['name']
        } for p in props]
        objs = {str(o.id): o for o in qs}

        def make_prop(pk, objs, props):
            if pk not in objs:
                return {p: {} for p in props}
            obj = objs[pk]
            result = {}
            for p in props:
                meta = self.REFINE_PROPOSE_PROPERTIES_DICT[p]
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

    @list_route(
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

        properties = self.REFINE_PROPOSE_PROPERTIES
        limit = request.GET.get('limit', len(properties))

        return Response({
            'properties': properties[:limit],
            'type': 'publicbody',
            'limit': limit
        })

    def get_serializer_context(self):
        ctx = super(PublicBodyViewSet, self).get_serializer_context()
        if self.action == 'search':
            ctx['facets'] = self.queryset.sqs.facet_counts()
        return ctx

    def get_searchqueryset(self, request):
        query = request.GET.get('q', '')
        sqs = SearchQuerySet().models(PublicBody).load_all()
        if len(query) > 2:
            sqs = sqs.filter(name_auto=AutoQuery(query))
        else:
            sqs = sqs.all()

        sqs = sqs.facet('jurisdiction', size=30)
        juris = request.GET.get('jurisdiction')
        if juris:
            sqs = sqs.filter(jurisdiction=juris)

        sqs = sqs.facet('classification', size=100)
        classification = request.GET.get('classification')
        if classification:
            sqs = sqs.filter(classification=classification)

        sqs = sqs.facet('categories', size=100)
        categories = request.GET.getlist('categories')
        if categories:
            for cat in categories:
                sqs = sqs.filter(categories=cat)

        return SearchQuerySetWrapper(sqs, PublicBody)
