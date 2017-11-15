from django.db.models import Q

from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import list_route

from haystack.query import SearchQuerySet

from froide.helper.search import SearchQuerySetWrapper
from froide.publicbody.api_views import PublicBodySerializer, FoiLawSerializer

from taggit.models import Tag

from .models import FoiRequest, FoiMessage, FoiAttachment


class FoiAttachmentSerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedIdentityField(
        view_name='api:attachment-detail',
        lookup_field='pk'
    )
    belongs_to = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='api:message-detail'
    )
    site_url = serializers.CharField(
        source='get_absolute_domain_url',
        read_only=True
    )
    anchor_url = serializers.CharField(
        source='get_domain_anchor_url',
        read_only=True
    )

    class Meta:
        model = FoiAttachment
        depth = 0
        fields = (
            'self', 'id', 'belongs_to', 'name', 'filetype',
            'approved', 'is_redacted', 'size', 'site_url', 'anchor_url'
        )


class FoiAttachmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FoiAttachmentSerializer

    def get_queryset(self):
        user = self.request.user
        vis_filter = Q(
            belongs_to__request__visibility=FoiRequest.VISIBLE_TO_PUBLIC,
            approved=True
        )
        if user.is_authenticated:
            vis_filter |= Q(belongs_to__request__user=user)
            if user.is_superuser:
                return FoiAttachment.objects.all()
        return FoiAttachment.objects.filter(vis_filter)


class FoiMessageSerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedIdentityField(
        view_name='api:message-detail',
        lookup_field='pk'
    )
    request = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='api:request-detail'
    )
    attachments = serializers.SerializerMethodField(
        source='get_attachments'
    )
    sender_public_body = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='api:publicbody-detail'
    )
    recipient_public_body = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='api:publicbody-detail'
    )

    subject = serializers.CharField(source='get_subject')
    content = serializers.CharField(source='get_content')
    sender = serializers.CharField()
    url = serializers.CharField(source='get_absolute_domain_url')
    status_name = serializers.CharField(source='get_status_display')

    class Meta:
        model = FoiMessage
        depth = 0
        fields = (
            'self', 'id', 'url', 'request', 'sent', 'is_response', 'is_postal',
            'is_escalation', 'content_hidden', 'sender_public_body',
            'recipient_public_body', 'status', 'timestamp',
            'redacted', 'not_publishable', 'attachments',
            'subject', 'content', 'sender', 'status_name'
        )

    def get_attachments(self, obj):
        user = self.context['request'].user
        atts = obj.foiattachment_set.all()
        if obj.request.user != user and not user.is_superuser:
            atts = atts.filter(approved=True)
        serializer = FoiAttachmentSerializer(
            atts,
            many=True,
            context={'request': self.context['request']}
        )
        return serializer.data


class FoiMessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FoiMessageSerializer

    def get_queryset(self):
        user = self.request.user
        vis_filter = Q(request__visibility=FoiRequest.VISIBLE_TO_PUBLIC)
        if user.is_authenticated:
            vis_filter |= Q(request__user=user)
            if user.is_superuser:
                return FoiMessage.objects.all()
        return FoiMessage.objects.filter(vis_filter)


class FoiRequestListSerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedIdentityField(
        view_name='api:request-detail',
        lookup_field='pk'
    )
    public_body = PublicBodySerializer(read_only=True)
    law = FoiLawSerializer(read_only=True)
    messages = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name='api:message-detail'
    )
    jurisdiction = serializers.HyperlinkedRelatedField(
        view_name='api:jurisdiction-detail',
        lookup_field='pk',
        read_only=True
    )

    class Meta:
        model = FoiRequest
        depth = 0
        fields = (
            'self',
            'id',
            'url',
            'jurisdiction',
            'is_foi', 'checked', 'refusal_reason',
            'costs',
            'public',
            'law',
            'same_as_count',
            'same_as',
            'due_date',
            'resolved_on', 'last_message', 'first_message',
            'status',
            'public_body',
            'resolution', 'slug',
            'title',
            'reference',
            'messages'
        )


class FoiRequestDetailSerializer(FoiRequestListSerializer):
    messages = FoiMessageSerializer(read_only=True, many=True)


class FoiRequestViewSet(viewsets.ReadOnlyModelViewSet):
    ordering_fields = ('first_message', 'last_message')
    serializer_action_classes = {
        'list': FoiRequestListSerializer,
        'retrieve': FoiRequestDetailSerializer
    }

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return FoiRequestListSerializer

    def get_queryset(self):
        user = self.request.user
        vis_filter = Q(visibility=FoiRequest.VISIBLE_TO_PUBLIC)
        if user.is_authenticated:
            vis_filter |= Q(user=user)
            if user.is_superuser:
                return FoiRequest.objects.all()
        return FoiRequest.objects.filter(vis_filter)

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
            tags = Tag.objects.filter(name__istartswith=query)
            tags = [t for t in tags.values_list('name', flat=True)]
        return Response(tags)

    def get_searchqueryset(self, request):
        query = request.GET.get('q', '')
        sqs = SearchQuerySet().models(FoiRequest).load_all()
        if len(query) > 2:
            sqs = sqs.auto_query(query)
        else:
            sqs = sqs.none()

        return SearchQuerySetWrapper(sqs, FoiRequest)
