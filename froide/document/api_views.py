from django.db.models import Q

from rest_framework import serializers, permissions, viewsets

from filingcabinet.api_views import (
    DocumentSerializer as FCDocumentSerializer,
    PageSerializer as FCPageSerializer,
    DocumentCollectionSerializer as FCDocumentCollectionSerializer,
    UpdateDocumentSerializer,
    DocumentViewSet as FCDocumentViewSet,
    DocumentCollectionViewSet as FCDocumentCollectionViewSet,
    PagesMixin
)
from filingcabinet.models import Page

from froide.helper.auth import can_write_object
from froide.helper.search.api_views import ESQueryMixin

from .models import Document, DocumentCollection
from .documents import PageDocument
from .filters import PageDocumentFilterset


class DocumentSerializer(FCDocumentSerializer):
    file_url = serializers.CharField(
        source='get_authorized_file_url',
        read_only=True
    )
    original = serializers.HyperlinkedRelatedField(
        view_name='api:attachment-detail',
        lookup_field='pk',
        read_only=True,
    )
    foirequest = serializers.HyperlinkedRelatedField(
        view_name='api:request-detail',
        lookup_field='pk',
        read_only=True,
    )
    publicbody = serializers.HyperlinkedRelatedField(
        view_name='api:publicbody-detail',
        lookup_field='pk',
        read_only=True,
    )

    class Meta:
        model = Document
        fields = FCDocumentSerializer.Meta.fields + (
            'original', 'foirequest', 'publicbody'
        )


class DocumentDetailSerializer(PagesMixin, DocumentSerializer):
    pages = serializers.SerializerMethodField(
        source='get_pages'
    )

    class Meta(DocumentSerializer.Meta):
        fields = DocumentSerializer.Meta.fields + (
            'pages',
        )


class DocumentCollectionSerializer(FCDocumentCollectionSerializer):
    class Meta:
        model = DocumentCollection
        fields = FCDocumentCollectionSerializer.Meta.fields


def filter_model(qs, user, token):
    vis_filter = Q(public=True)
    if user.is_authenticated:
        # Either not OAuth or OAuth and valid token
        if not token and user.is_superuser:
            return qs
        if not token or token.is_valid(['read:document']):
            vis_filter |= Q(user=user)
    return qs.filter(vis_filter)


class AllowedOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if can_write_object(obj, request):
            return True

        if request.method in permissions.SAFE_METHODS:
            return obj.public

        return False


class PageSerializer(FCPageSerializer):
    query_highlight = serializers.CharField()

    class Meta(FCPageSerializer.Meta):
        fields = FCPageSerializer.Meta.fields + (
            'query_highlight',
        )


class PageViewSet(ESQueryMixin, viewsets.GenericViewSet):
    serializer_class = PageSerializer
    search_model = Page
    search_document = PageDocument
    read_token_scopes = ['read:request']
    searchfilterset_class = PageDocumentFilterset

    def list(self, request, *args, **kwargs):
        return self.search_view(request)


class DocumentViewSet(FCDocumentViewSet):
    serializer_action_classes = {
        'list': DocumentSerializer,
        'retrieve': DocumentDetailSerializer,
        'update': UpdateDocumentSerializer
    }
    permission_classes = (AllowedOrReadOnly,)

    def get_queryset(self):
        user = self.request.user
        token = self.request.auth
        return filter_model(Document.objects.all(), user, token)


class DocumentCollectionViewSet(FCDocumentCollectionViewSet):
    serializer_action_classes = {
        'list': DocumentCollectionSerializer,
        'retrieve': DocumentCollectionSerializer,

    }
    permission_classes = (AllowedOrReadOnly,)

    def get_queryset(self):
        user = self.request.user
        token = self.request.auth
        return filter_model(
            DocumentCollection.objects.all(), user, token
        )
