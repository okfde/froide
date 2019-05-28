from django.db.models import Q
from django.contrib.auth import get_user_model

from rest_framework import serializers, viewsets, mixins, status, throttling
from rest_framework.response import Response
from rest_framework.decorators import action

from oauth2_provider.contrib.rest_framework import TokenHasScope

from django_filters import rest_framework as filters

from elasticsearch_dsl.query import Q as ESQ

from froide.helper.search import SearchQuerySetWrapper
from froide.helper.api_utils import ElasticLimitOffsetPagination
from froide.publicbody.api_views import (
    FoiLawSerializer, SimplePublicBodySerializer, PublicBodySerializer
)

from taggit.models import Tag

from froide.publicbody.models import PublicBody
from froide.campaign.models import Campaign

from .models import FoiRequest, FoiMessage, FoiAttachment
from .services import CreateRequestService
from .validators import clean_reference
from .utils import check_throttle
from .auth import can_read_foirequest_authenticated
from .documents import FoiRequestDocument


User = get_user_model()


def filter_foirequests(user, token):
    vis_filter = Q(visibility=FoiRequest.VISIBLE_TO_PUBLIC)
    if user.is_authenticated:
        # Either not OAuth or OAuth and valid token
        if not token and user.is_superuser:
            return FoiRequest.objects.all()
        if not token or token.is_valid(['read:request']):
            vis_filter |= Q(user=user)
    return FoiRequest.objects.filter(vis_filter)


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


def filter_by_authenticated_user_queryset(request):
    if request is None or not request.user.is_authenticated:
        return User.objects.none()

    user = request.user
    token = request.auth

    if not token and user.is_superuser:
        # Allow superusers complete access
        return User.objects.all()

    if not token or token.is_valid(['read:request']):
        # allow filter by own user
        return User.objects.filter(id=user.id)
    return User.objects.none()


class FoiAttachmentSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name='api:attachment-detail',
        lookup_field='pk'
    )
    converted = serializers.HyperlinkedRelatedField(
        view_name='api:attachment-detail',
        lookup_field='pk',
        read_only=True,
    )
    redacted = serializers.HyperlinkedRelatedField(
        view_name='api:attachment-detail',
        lookup_field='pk',
        read_only=True,
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
    file_url = serializers.SerializerMethodField(
        source='get_file_url',
        read_only=True
    )
    pending = serializers.SerializerMethodField(
        source='get_pending',
        read_only=True
    )

    class Meta:
        model = FoiAttachment
        depth = 0
        fields = (
            'resource_uri', 'id', 'belongs_to', 'name', 'filetype',
            'size', 'site_url', 'anchor_url', 'file_url', 'pending',
            'is_converted', 'converted',
            'approved', 'can_approve',
            'redacted', 'is_redacted', 'can_redact',
            'can_delete',
            'is_pdf', 'is_image', 'is_irrelevant',
        )

    def get_file_url(self, obj):
        return obj.get_absolute_domain_file_url(authorized=True)

    def get_pending(self, obj):
        return obj.pending


class FoiAttachmentFilter(filters.FilterSet):
    class Meta:
        model = FoiAttachment
        fields = (
            'name', 'filetype', 'approved', 'is_redacted', 'belongs_to',
        )


class FoiAttachmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FoiAttachmentSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FoiAttachmentFilter

    def get_queryset(self):
        user = self.request.user
        token = self.request.auth

        vis_filter = Q(
            belongs_to__request__visibility=FoiRequest.VISIBLE_TO_PUBLIC,
            approved=True
        )

        if user.is_authenticated:
            if not token and user.is_superuser:
                return self.optimize_query(FoiAttachment.objects.all())
            if not token or token.is_valid(['read:request']):
                vis_filter |= Q(belongs_to__request__user=user)
        return self.optimize_query(FoiAttachment.objects.filter(vis_filter))

    def optimize_query(self, qs):
        return qs.prefetch_related(
            'belongs_to',
            'belongs_to__request',
            'belongs_to__request__user',
        )


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
            'resource_uri', 'id', 'url', 'request', 'sent', 'is_response',
            'is_postal', 'kind',
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
                return self.optimize_query(FoiMessage.objects.all())
            if not token or token.is_valid(['read:request']):
                vis_filter |= Q(request__user=user)
        return self.optimize_query(FoiMessage.objects.filter(vis_filter))

    def optimize_query(self, qs):
        return qs.prefetch_related(
            'request',
            'request__user',
            'sender_user',
            'foiattachment_set'
        )


class FoiRequestListSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name='api:request-detail',
        lookup_field='pk'
    )
    public_body = SimplePublicBodySerializer(read_only=True)
    law = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:law-detail', lookup_field='pk'
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
    project = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )
    campaign = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='api:campaign-detail',
        lookup_field='pk'
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
            'user',
            'project',
            'campaign',
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
    public_body = PublicBodySerializer(read_only=True)
    law = FoiLawSerializer(read_only=True)
    messages = FoiMessageSerializer(read_only=True, many=True)

    class Meta(FoiRequestListSerializer.Meta):
        fields = FoiRequestListSerializer.Meta.fields + ('messages',)


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
    categories = filters.CharFilter(method='categories_filter')
    reference = filters.CharFilter(method='reference_filter')
    follower = filters.ModelChoiceFilter(
        queryset=filter_by_authenticated_user_queryset,
        method='follower_filter'
    )
    costs = filters.RangeFilter()
    campaign = filters.ModelChoiceFilter(
        queryset=Campaign.objects.filter(public=True),
        null_value='-',
        null_label='No Campaign',
        lookup_expr='isnull',
        method='campaign_filter'
    )

    # FIXME: default ordering should be undetermined?
    # ordering = filters.OrderingFilter(
    #     fields=(
    #         ('last_message', 'last_message'),
    #         ('first_message', 'first_message')
    #     ),
    #     field_labels={
    #         '-last_message': 'By last message (latest first)',
    #         '-first_message': 'By first message (latest first)',
    #         'last_message': 'By last message (oldest first)',
    #         'first_message': 'By first message (oldest first)',
    #     }
    # )

    class Meta:
        model = FoiRequest
        fields = (
            'user', 'is_foi', 'checked', 'jurisdiction', 'tags',
            'resolution', 'status', 'reference', 'public_body',
            'slug', 'costs', 'project', 'campaign'
        )

    def tag_filter(self, queryset, name, value):
        return queryset.filter(**{
            'tags__name': value,
        })

    def categories_filter(self, queryset, name, value):
        return queryset.filter(**{
            'public_body__categories__name': value,
        })

    def reference_filter(self, queryset, name, value):
        return queryset.filter(**{
            'reference__startswith': value,
        })

    def follower_filter(self, queryset, name, value):
        return queryset.filter(followers__user=value)

    def campaign_filter(self, queryset, name, value):
        if value == '-':
            return queryset.filter(campaign__isnull=True)
        return queryset.filter(campaign=value)


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
    serializer_action_classes = {
        'create': MakeRequestSerializer,
        'list': FoiRequestListSerializer,
        'retrieve': FoiRequestDetailSerializer
    }
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FoiRequestFilter
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
        return self.optimize_query(filter_foirequests(user, token))

    def optimize_query(self, qs):
        extras = ()
        if self.action == 'retrieve':
            extras = (
                'law',
            )
        qs = qs.prefetch_related(
            'public_body',
            'user',
            'public_body__jurisdiction',
            *extras
        )
        return qs

    @action(detail=False, methods=['get'])
    def search(self, request):
        self.sqs = self.get_searchqueryset(request)

        paginator = ElasticLimitOffsetPagination()
        paginator.paginate_queryset(self.sqs, self.request, view=self)

        self.queryset = self.optimize_query(self.sqs.to_queryset())

        serializer = self.get_serializer(self.queryset, many=True)
        data = serializer.data

        return paginator.get_paginated_response(data)

    @action(detail=False, methods=['get'], url_path='tags/autocomplete',
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

        user = self.request.user
        token = self.request.auth

        s = FoiRequestDocument.search()
        if user.is_authenticated:
            # Either not OAuth or OAuth and valid token
            if not token and user.is_superuser:
                # No filters for super users
                pass
            elif not token or token.is_valid(['read:request']):
                s = s.filter('bool', should=[
                    # Bool query in filter context
                    # at least one should clause is required to match.
                    ESQ('term', public=True),
                    ESQ('term', user=user.pk),
                ])
            else:
                s = s.filter('term', public=True)
        else:
            s = s.filter('term', public=True)

        sqs = SearchQuerySetWrapper(
            s,
            FoiRequest
        )

        if len(query) > 2:
            sqs = sqs.set_query(ESQ(
                "multi_match",
                query=query,
                fields=['content', 'title', 'description']
            ))

        return sqs

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
