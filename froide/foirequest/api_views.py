from __future__ import unicode_literals

from django.db.models import Q
from django.contrib.auth import get_user_model

from rest_framework import serializers, viewsets, mixins, status, throttling
from rest_framework.response import Response
from rest_framework.decorators import list_route

from oauth2_provider.contrib.rest_framework import TokenHasScope

from django_filters import rest_framework as filters

from haystack.query import SearchQuerySet

from froide.helper.search import SearchQuerySetWrapper
from froide.publicbody.api_views import PublicBodySerializer, FoiLawSerializer

from taggit.models import Tag

from froide.publicbody.models import PublicBody

from .models import FoiRequest, FoiMessage, FoiAttachment
from .services import CreateRequestService
from .validators import clean_reference
from .utils import check_throttle
from .auth import can_read_foirequest_authenticated


User = get_user_model()


def filter_by_user_queryset(request):
    user_filter = Q(is_active=True, private=False)
    if request is None or not request.user.is_authenticated:
        return User.objects.filter(user_filter)

    user = request.user
    token = request.auth

    if not token and user.is_superuser:
        return User.objects.all()

    # Either not OAuth or OAuth and valid token
    if not token or token.is_valid(['read:request']):
        # allow filter by own user
        user_filter |= Q(pk=request.user.pk)

    return User.objects.filter(user_filter)


class FoiAttachmentSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
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
            'resource_uri', 'id', 'belongs_to', 'name', 'filetype',
            'approved', 'is_redacted', 'size', 'site_url', 'anchor_url'
        )


class FoiAttachmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FoiAttachmentSerializer

    def get_queryset(self):
        user = self.request.user
        token = self.request.auth

        vis_filter = Q(
            belongs_to__request__visibility=FoiRequest.VISIBLE_TO_PUBLIC,
            approved=True
        )

        if user.is_authenticated:
            if not token and user.is_superuser:
                return FoiAttachment.objects.all()
            if not token or token.is_valid(['read:request']):
                vis_filter |= Q(belongs_to__request__user=user)
        return FoiAttachment.objects.filter(vis_filter)


class FoiMessageSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
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
            'resource_uri', 'id', 'url', 'request', 'sent', 'is_response', 'is_postal',
            'is_escalation', 'content_hidden', 'sender_public_body',
            'recipient_public_body', 'status', 'timestamp',
            'redacted', 'not_publishable', 'attachments',
            'subject', 'content', 'sender', 'status_name'
        )

    def get_attachments(self, obj):
        request = self.context['request']
        token = request.auth

        atts = obj.foiattachment_set.all()
        if not self.can_see_attachment(obj.request, request, token):
            atts = atts.filter(approved=True)
        serializer = FoiAttachmentSerializer(
            atts,
            many=True,
            context={'request': self.context['request']}
        )
        return serializer.data

    def can_see_attachment(self, foirequest, request, token):
        allowed = can_read_foirequest_authenticated(
            foirequest, request, allow_code=False
        )
        if allowed:
            if token and not token.is_valid(['read:request']):
                return False
            return True
        return False


class FoiMessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FoiMessageSerializer

    def get_queryset(self):
        user = self.request.user
        token = self.request.auth

        vis_filter = Q(request__visibility=FoiRequest.VISIBLE_TO_PUBLIC)

        if user.is_authenticated:
            if not token and user.is_superuser:
                return FoiMessage.objects.all()
            if not token or token.is_valid(['read:request']):
                vis_filter |= Q(request__user=user)
        return FoiMessage.objects.filter(vis_filter)


class FoiRequestListSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
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
    same_as = serializers.HyperlinkedRelatedField(
        view_name='api:request-detail',
        lookup_field='pk',
        read_only=True
    )
    user = serializers.SerializerMethodField(
        source='get_user'
    )

    class Meta:
        model = FoiRequest
        depth = 0
        fields = (
            'resource_uri',
            'id',
            'url',
            'jurisdiction',
            'is_foi', 'checked', 'refusal_reason',
            'costs',
            'public',
            'law',
            'description',
            'summary',
            'same_as_count',
            'same_as',
            'due_date',
            'resolved_on', 'last_message', 'first_message',
            'status',
            'public_body',
            'resolution', 'slug',
            'title',
            'reference',
            'messages',
            'user'
        )

    def get_user(self, obj):
        if obj.user is None:
            return None
        user = self.context['request'].user
        if obj.user == user or user.is_superuser:
            return obj.user.pk
        if obj.user.private:
            return None
        return obj.user.pk


class FoiRequestDetailSerializer(FoiRequestListSerializer):
    messages = FoiMessageSerializer(read_only=True, many=True)


class MakeRequestSerializer(serializers.Serializer):
    publicbodies = serializers.PrimaryKeyRelatedField(
        queryset=PublicBody.objects.all(),
        many=True
    )

    subject = serializers.CharField(max_length=230)
    body = serializers.CharField()

    full_text = serializers.BooleanField(required=False, default=False)
    public = serializers.BooleanField(required=False, default=True)
    reference = serializers.CharField(required=False, default='')
    tags = serializers.ListField(
        required=False,
        child=serializers.CharField(max_length=255)
    )

    def validate_reference(self, value):
        cleaned_reference = clean_reference(value)
        if value and cleaned_reference != value:
            raise serializers.ValidationError('Reference not clean')
        return cleaned_reference

    def create(self, validated_data):
        service = CreateRequestService(validated_data)
        return service.execute(validated_data['request'])


class FoiRequestFilter(filters.FilterSet):
    user = filters.ModelChoiceFilter(queryset=filter_by_user_queryset)
    tags = filters.CharFilter(method='tag_filter')

    class Meta:
        model = FoiRequest
        fields = (
            'user', 'is_foi', 'checked', 'jurisdiction', 'tags',
            'resolution', 'status', 'reference', 'public_body'
        )

    def tag_filter(self, queryset, name, value):
        return queryset.filter(**{
            'tags__name': value,
        })


class CreateOnlyWithScopePermission(TokenHasScope):
    def has_permission(self, request, view):
        if view.action not in ('create', 'update'):
            return True
        if not request.user.is_authenticated:
            return False
        return super(CreateOnlyWithScopePermission, self).has_permission(
            request, view
        )


class MakeRequestThrottle(throttling.BaseThrottle):
    def allow_request(self, request, view):
        return not bool(check_throttle(request.user, FoiRequest))


def throttle_action(throttle_classes):
    def inner(method):
        def _inner(self, request, *args, **kwargs):
            for throttle_class in throttle_classes:
                throttle = throttle_class()
                if not throttle.allow_request(request, self):
                    self.throttled(request, throttle.wait())
            return method(self, request, *args, **kwargs)
        return _inner
    return inner


class FoiRequestViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    ordering_fields = ('first_message', 'last_message')
    serializer_action_classes = {
        'create': MakeRequestSerializer,
        'list': FoiRequestListSerializer,
        'retrieve': FoiRequestDetailSerializer
    }
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = FoiRequestFilter
    permission_classes = (CreateOnlyWithScopePermission,)
    required_scopes = ['make:request']

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return FoiRequestListSerializer

    def get_queryset(self):
        user = self.request.user
        token = self.request.auth
        vis_filter = Q(visibility=FoiRequest.VISIBLE_TO_PUBLIC)
        if user.is_authenticated:
            # Either not OAuth or OAuth and valid token
            if not token and user.is_superuser:
                return FoiRequest.objects.all()
            if not token or token.is_valid(['read:request']):
                vis_filter |= Q(user=user)
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

    @throttle_action((MakeRequestThrottle,))
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        data = {
            'status': 'success',
            'url': instance.get_absolute_domain_url()
        }
        headers = {'Location': str(instance.get_absolute_url())}
        return Response(data, status=status.HTTP_201_CREATED,
            headers=headers)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user, request=self.request)
