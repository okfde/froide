from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import list_route

from django_filters import rest_framework as filters

from haystack.query import SearchQuerySet
from haystack.inputs import AutoQuery

from froide.helper.search import SearchQuerySetWrapper

from .models import PublicBody, PublicBodyTag, Jurisdiction, FoiLaw


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


class PublicBodyTagSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PublicBodyTag
        fields = (
            'id', 'name', 'slug', 'rank', 'is_topic'
        )


class PublicBodyTagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PublicBodyTagSerializer
    queryset = PublicBodyTag.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('is_topic', 'rank',)


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
    tags = PublicBodyTagSerializer(read_only=True, many=True)
    site_url = serializers.CharField(source='get_absolute_domain_url')

    class Meta:
        model = PublicBody
        depth = 0
        fields = (
            'resource_uri', 'id', 'name', 'slug', 'other_names',
            'description', 'url', 'parent', 'root',
            'depth', 'classification', 'classification_slug',
            'email', 'contact', 'address',
            'request_note', 'number_of_requests',
            'laws', 'site_url',
            'jurisdiction', 'request_note_html',
            'default_law', 'tags'
        )


class PublicBodyFilter(filters.FilterSet):
    tags = filters.CharFilter(method='tag_filter')

    class Meta:
        model = PublicBody
        fields = (
            'jurisdiction', 'tags', 'slug'
        )

    def tag_filter(self, queryset, name, value):
        return queryset.filter(**{
            'tags__name': value,
        })


class PublicBodyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PublicBodySerializer
    queryset = PublicBody.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = PublicBodyFilter

    @list_route(methods=['get'])
    def search(self, request):
        queryset = self.get_searchqueryset(request)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @list_route(methods=['get'], url_path='tags/autocomplete',
                url_name='tags-autocomplete')
    def tags_autocomplete(self, request):
        query = request.GET.get('query', '')
        tags = []
        if query:
            tags = PublicBodyTag.objects.filter(name__istartswith=query)
            kind = request.GET.get('kind', '')
            if kind:
                tags = tags.filter(kind=kind)
            tags = [t for t in tags.values_list('name', flat=True)]
        return Response(tags)

    def get_searchqueryset(self, request):
        query = request.GET.get('q', '')
        sqs = SearchQuerySet().models(PublicBody).load_all()
        if len(query) > 2:
            sqs = sqs.filter(name_auto=AutoQuery(query))
        else:
            sqs = sqs.all()

        juris = request.GET.get('jurisdiction')
        if juris:
            sqs = sqs.filter(jurisdiction__exact=juris)

        tags = request.GET.get('tags')
        if tags:
            sqs = sqs.filter(tags__exact=tags)

        return SearchQuerySetWrapper(sqs, PublicBody)
