from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import list_route

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
