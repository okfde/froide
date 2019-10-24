from django.utils import timezone
from django.db.models import (
    Count, Subquery, Exists, OuterRef, Value, NullBooleanField,
    Case, When
)

from rest_framework import serializers, viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.reverse import reverse

from oauth2_provider.contrib.rest_framework import TokenHasScope

from froide.foirequest.models.request import (
    FoiRequest, get_absolute_domain_short_url
)
from froide.foirequest.api_views import filter_foirequests
from froide.helper.api_utils import CustomLimitOffsetPagination

from .models import FoiRequestFollower


class CreateOnlyWithScopePermission(TokenHasScope):
    def has_permission(self, request, view):
        if view.action not in ('create', 'update'):
            return True
        if not request.user.is_authenticated:
            return False
        if not request.auth:
            return True
        return super(CreateOnlyWithScopePermission, self).has_permission(
            request, view
        )


class CreateFoiRequestFollowSerializer(serializers.ModelSerializer):
    request = serializers.PrimaryKeyRelatedField(queryset=FoiRequest.objects.none())

    class Meta:
        model = FoiRequestFollower
        fields = ('request',)

    def __init__(self, *args, **kwargs):
        super(CreateFoiRequestFollowSerializer, self).__init__(
            *args, **kwargs
        )
        qs = FoiRequestFollower.objects.get_followable_requests(
            self.context['view'].request.user
        )
        self.fields['request'].queryset = qs

    def validate_request(self, value):
        """
        Check that the blog post is about Django.
        """

        user = self.context['view'].request.user
        token = self.context['view'].request.auth
        qs = filter_foirequests(user, token)
        try:
            value = qs.get(id=value.id)
        except FoiRequest.DoesNotExist:
            raise serializers.ValidationError('No access')
        if value.user == user:
            raise serializers.ValidationError('Cannot follow your own requests')
        return value

    def create(self, validated_data):
        follower, create = FoiRequestFollower.objects.get_or_create(
            request=validated_data['request'],
            user=validated_data['user'],
            defaults={
                'timestamp': timezone.now(),
                'confirmed': True
            }
        )
        return follower


class FoiRequestFollowSerializer(serializers.HyperlinkedModelSerializer):
    request = serializers.HyperlinkedRelatedField(
        view_name='api:request-detail',
        lookup_field='pk',
        read_only=True
    )
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name='api:following-detail',
        lookup_field='pk',
        required=False
    )
    request_url = serializers.SerializerMethodField(
        source='get_absolute_domain_url',
        read_only=True
    )
    follow_count = serializers.IntegerField(read_only=True)
    follows = serializers.BooleanField(read_only=True)
    can_follow = serializers.BooleanField(read_only=True)

    class Meta:
        model = FoiRequestFollower
        fields = ('resource_uri', 'request', 'request_url',
                  'timestamp', 'follow_count', 'follows', 'can_follow')

    def get_request_url(self, obj):
        return get_absolute_domain_short_url(obj.request_id)


class FoiRequestFollowRequestSerializer(serializers.HyperlinkedModelSerializer):
    request = serializers.HyperlinkedIdentityField(
        view_name='api:request-detail',
        lookup_field='pk',
        read_only=True
    )
    resource_uri = serializers.HyperlinkedRelatedField(
        view_name='api:following-detail',
        lookup_field='pk',
        read_only=True
    )
    request_url = serializers.SerializerMethodField(
        source='get_absolute_domain_url',
        read_only=True
    )
    follow_count = serializers.IntegerField(read_only=True)
    follows = serializers.BooleanField(read_only=True)
    can_follow = serializers.BooleanField(read_only=True)

    class Meta:
        model = FoiRequest
        fields = ('request', 'request_url', 'resource_uri',
                  'follow_count', 'follows', 'can_follow')

    def get_request_url(self, obj):
        return get_absolute_domain_short_url(obj.id)


class LargeResultsSetPagination(CustomLimitOffsetPagination):
    default_limit = 150
    max_limit = 200


class FoiRequestFollowerViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.DestroyModelMixin,
                        viewsets.GenericViewSet):
    serializer_class = FoiRequestFollowSerializer
    permission_classes = (CreateOnlyWithScopePermission,)
    read_scopes = ['read:request']
    required_scopes = ['follow:request']
    pagination_class = LargeResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateFoiRequestFollowSerializer
        if self.get_request_filter():
            return FoiRequestFollowRequestSerializer
        return self.serializer_class

    def get_foirequest_queryset(self, requests=None):
        if self.action != 'list':
            raise Exception('Bad call to foirequest queryset')
        user = self.request.user
        token = self.request.auth
        qs = filter_foirequests(user, token)
        if requests is not None:
            qs = qs.filter(id__in=requests)
        if user.is_authenticated and (
                not token or token.is_valid(self.read_scopes)):
            follows = (
                FoiRequestFollower.objects
                .filter(request_id=OuterRef('pk'), user=user)
            )
            qs = qs.annotate(
                follows=Exists(follows),
                resource_uri=Subquery(follows.values('pk')),
                can_follow=Case(
                    When(user_id=user.id, then=Value(False)),
                    default=Value(True),
                    output_field=NullBooleanField()
                )
            )
        else:
            qs = qs.annotate(
                follows=Value(None, output_field=NullBooleanField()),
                can_follow=Value(None, output_field=NullBooleanField())
            )
        qs = qs.annotate(
            follow_count=Count('followers'),
        )
        return qs

    def get_request_filter(self):
        if not hasattr(self, '_requests_filter'):
            requests = self.request.query_params.get('request', '').split(',')
            try:
                requests = [int(r) for r in requests]
            except ValueError:
                requests = []
            self._requests_filter = requests
        return self._requests_filter

    def get_queryset(self):
        user = self.request.user
        token = self.request.auth
        requests = self.get_request_filter()
        qs = None
        if requests and self.action == 'list':
            # Never return on destructive action
            return self.get_foirequest_queryset(requests=requests)
        elif user.is_authenticated:
            if not token or token.is_valid(self.read_scopes):
                qs = (
                    FoiRequestFollower.objects
                    .filter(user=user)
                    .order_by('-timestamp')
                )
        if qs is None:
            qs = FoiRequestFollower.objects.none()

        if self.action == 'list':
            follower_count = (
                FoiRequest.objects
                .filter(id=OuterRef('request'))
                .values('pk')
                .annotate(count=Count('followers'))
            )
            qs = qs.annotate(
                follow_count=Subquery(follower_count.values('count')),
                # follows by query definition
                follows=Value(True, output_field=NullBooleanField()),
                # can_follow by query definition
                can_follow=Value(True, output_field=NullBooleanField())
            )
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        data = {
            'status': 'success',
            'url': reverse('api:following-detail', kwargs={'pk': instance.pk},
                           request=request)
        }
        headers = {'Location': data['url']}
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)
