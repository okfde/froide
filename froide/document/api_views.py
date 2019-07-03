from django.db.models import Q

from rest_framework import serializers, permissions

from filingcabinet.api_views import (
    DocumentSerializer as FCDocumentSerializer,
    UpdateDocumentSerializer,
    DocumentViewSet as FCDocumentViewSet,
    PagesMixin
)

from froide.helper.auth import can_write_object

from .models import Document


class DocumentSerializer(FCDocumentSerializer):
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


def filter_documents(user, token):
    vis_filter = Q(public=True)
    if user.is_authenticated:
        # Either not OAuth or OAuth and valid token
        if not token and user.is_superuser:
            return Document.objects.all()
        if not token or token.is_valid(['read:document']):
            vis_filter |= Q(user=user)
    return Document.objects.filter(vis_filter)


class AllowedOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if can_write_object(obj, request):
            return True

        if request.method in permissions.SAFE_METHODS:
            return obj.public

        return False


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
        return filter_documents(user, token)
