from django.db.models import Q, Prefetch
from django.contrib.auth import get_user_model

from rest_framework import serializers, viewsets, mixins, status, throttling
from rest_framework.response import Response
from rest_framework.decorators import action

from oauth2_provider.contrib.rest_framework import TokenHasScope

from django_filters import rest_framework as filters

from froide.helper.search.api_views import ESQueryMixin
from froide.helper.text_diff import get_differences
from froide.publicbody.api_views import (
    FoiLawSerializer, SimplePublicBodySerializer, PublicBodySerializer
)

from taggit.models import Tag

from froide.publicbody.models import PublicBody
from froide.campaign.models import Campaign
from froide.document.api_views import DocumentSerializer

from .models import FoiRequest, FoiMessage, FoiAttachment
from .services import CreateRequestService
from .validators import clean_reference
from .utils import check_throttle
from .auth import (
    can_read_foirequest_authenticated, get_read_foirequest_queryset,
    get_read_foimessage_queryset, get_read_foiattachment_queryset
)
from .documents import FoiRequestDocument
from .filters import FoiRequestFilterSet


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
    document = DocumentSerializer()
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
            'document'
        )

    def get_file_url(self, obj):
        return obj.get_absolute_domain_file_url(authorized=True)


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
        qs = get_read_foiattachment_queryset(self.request)
        return self.optimize_query(qs)

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
    redacted_subject = serializers.SerializerMethodField(source='get_redacted_subject')
    redacted_content = serializers.SerializerMethodField(source='get_redacted_content')
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
            'subject', 'content',
            'redacted_subject',
            'redacted_content',
            'sender', 'status_name'
        )

    def get_redacted_subject(self, obj):
        request = self.context['request']

        if can_read_foirequest_authenticated(
            obj.request, request, allow_code=False
        ):
            show, hide = obj.subject, obj.subject_redacted
        else:
            show, hide = obj.subject_redacted, obj.subject
        return list(get_differences(show, hide))

    def get_redacted_content(self, obj):
        request = self.context['request']

        if can_read_foirequest_authenticated(
            obj.request, request, allow_code=False
        ):
            show, hide = obj.plaintext, obj.plaintext_redacted
        else:
            show, hide = obj.plaintext_redacted, obj.plaintext
        return list(get_differences(show, hide))

    def get_attachments(self, obj):
        if not hasattr(obj, 'visible_attachments'):
            obj.visible_attachments = get_read_foiattachment_queryset(
                self.context['request'],
                queryset=FoiAttachment.objects.filter(belongs_to=obj)
            )

        serializer = FoiAttachmentSerializer(
            obj.visible_attachments,  # already filtered by prefetch
            many=True,
            context={'request': self.context['request']}
        )
        return serializer.data


class FoiMessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FoiMessageSerializer

    def get_queryset(self):
        qs = get_read_foimessage_queryset(self.request).order_by()
        return self.optimize_query(qs)

    def optimize_query(self, qs):
        return optimize_message_queryset(self.request, qs)


def optimize_message_queryset(request, qs):
    atts = get_read_foiattachment_queryset(
        request,
        queryset=FoiAttachment.objects.filter(belongs_to__in=qs)
    )
    return qs.prefetch_related(
        'request',
        'request__user',
        'sender_user',
        'sender_public_body',
        Prefetch(
            'foiattachment_set',
            queryset=atts,
            to_attr='visible_attachments'
        )
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
    messages = serializers.SerializerMethodField()

    class Meta(FoiRequestListSerializer.Meta):
        fields = FoiRequestListSerializer.Meta.fields + ('messages',)

    def get_messages(self, obj):
        qs = optimize_message_queryset(
            self.context['request'], FoiMessage.objects.filter(request=obj)
        )
        return FoiMessageSerializer(
            qs, read_only=True, many=True,
            context=self.context
        ).data


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
                        ESQueryMixin,
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
    search_model = FoiRequest
    search_document = FoiRequestDocument
    read_token_scopes = ['read:request']
    searchfilterset_class = FoiRequestFilterSet

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return FoiRequestListSerializer

    def get_queryset(self):
        qs = get_read_foirequest_queryset(self.request)
        return self.optimize_query(qs)

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
        return self.search_view(request)

    @action(detail=False, methods=['get'], url_path='tags/autocomplete',
                url_name='tags-autocomplete')
    def tags_autocomplete(self, request):
        query = request.GET.get('query', '')
        tags = []
        if query:
            tags = Tag.objects.filter(name__istartswith=query)
            tags = [t for t in tags.values_list('name', flat=True)]
        return Response(tags)

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
