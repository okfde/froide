from django.contrib.auth import get_user_model
from django.db.models import Q

from django_filters import rest_framework as filters
from rest_framework import mixins, permissions, status, throttling, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from taggit.models import Tag

from froide.campaign.models import Campaign
from froide.foirequest.permissions import WriteFoiRequestPermission
from froide.helper.search.api_views import ESQueryMixin

from ..auth import (
    CreateOnlyWithScopePermission,
    FoiRequestScope,
    get_read_foirequest_queryset,
    get_write_foirequest_queryset,
    throttle_action,
)
from ..documents import FoiRequestDocument
from ..filters import FoiRequestFilterSet
from ..models import FoiRequest
from ..serializers import (
    FoiRequestDetailSerializer,
    FoiRequestListSerializer,
    MakeRequestSerializer,
)
from ..utils import check_throttle

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
    if not token or token.is_valid([FoiRequestScope.READ_REQUEST]):
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

    if not token or token.is_valid([FoiRequestScope.READ_REQUEST]):
        # allow filter by own user
        return User.objects.filter(id=user.id)
    return User.objects.none()


class FoiRequestFilter(filters.FilterSet):
    user = filters.ModelChoiceFilter(queryset=filter_by_user_queryset)
    tags = filters.CharFilter(method="tag_filter")
    categories = filters.CharFilter(method="categories_filter")
    classification = filters.CharFilter(method="classification_filter")
    # FIXME
    # jurisdiction = filters.CharFilter(method="jurisdiction_filter")
    reference = filters.CharFilter(method="reference_filter")
    follower = filters.ModelChoiceFilter(
        queryset=filter_by_authenticated_user_queryset, method="follower_filter"
    )
    costs = filters.RangeFilter()
    # TODO i18n
    campaign = filters.ModelChoiceFilter(
        queryset=Campaign.objects.filter(public=True),
        null_value="-",
        null_label="No Campaign",
        lookup_expr="isnull",
        method="campaign_filter",
    )
    created_at_after = filters.DateFilter(field_name="created_at", lookup_expr="gte")
    created_at_before = filters.DateFilter(field_name="created_at", lookup_expr="lt")
    has_same = filters.BooleanFilter(
        field_name="same_as", lookup_expr="isnull", exclude=True
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
            "user",
            "is_foi",
            "checked",
            "jurisdiction",
            "tags",
            "resolution",
            "status",
            "reference",
            "classification",
            "public_body",
            "slug",
            "costs",
            "project",
            "campaign",
            "law",
        )

    def tag_filter(self, queryset, name, value):
        return queryset.filter(
            **{
                "tags__name": value,
            }
        )

    def categories_filter(self, queryset, name, value):
        return queryset.filter(
            **{
                "public_body__categories__name": value,
            }
        )

    def classification_filter(self, queryset, name, value):
        return queryset.filter(
            **{
                "public_body__classification__name": value,
            }
        )

    def reference_filter(self, queryset, name, value):
        return queryset.filter(
            **{
                "reference__startswith": value,
            }
        )

    def follower_filter(self, queryset, name, value):
        return queryset.filter(followers__user=value)

    def campaign_filter(self, queryset, name, value):
        if value == "-":
            return queryset.filter(campaign__isnull=True)
        return queryset.filter(campaign=value)


class MakeRequestThrottle(throttling.BaseThrottle):
    def allow_request(self, request, view):
        return not bool(check_throttle(request.user, FoiRequest))


class FoiRequestViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    ESQueryMixin,
    viewsets.GenericViewSet,
):
    serializer_action_classes = {
        "create": MakeRequestSerializer,
        "list": FoiRequestListSerializer,
        "update": FoiRequestListSerializer,
        "retrieve": FoiRequestDetailSerializer,
    }
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FoiRequestFilter
    permission_classes = (CreateOnlyWithScopePermission, WriteFoiRequestPermission)
    required_scopes = [FoiRequestScope.MAKE_REQUEST]
    search_model = FoiRequest
    search_document = FoiRequestDocument
    read_token_scopes = [FoiRequestScope.READ_REQUEST]
    searchfilterset_class = FoiRequestFilterSet

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return FoiRequestListSerializer

    def get_queryset(self):
        if self.request.method in permissions.SAFE_METHODS:
            qs = get_read_foirequest_queryset(self.request)
        else:
            qs = get_write_foirequest_queryset(self.request)
        return self.optimize_query(qs)

    def optimize_query(self, qs):
        extras = ()
        if self.action == "retrieve":
            extras = ("law",)
        qs = qs.prefetch_related(
            "public_body", "user", "tags", "public_body__jurisdiction", *extras
        )
        return qs

    @action(detail=False, methods=["get"])
    def search(self, request):
        return self.search_view(request)

    @action(
        detail=False,
        methods=["get"],
        url_path="tags/autocomplete",
        url_name="tags-autocomplete",
    )
    def tags_autocomplete(self, request):
        query = request.GET.get("q", "")
        tags = Tag.objects.none()
        if query:
            tags = (
                Tag.objects.filter(name__istartswith=query)
                .only("name")
                .order_by("name")
            )

        page = self.paginate_queryset(tags)
        return self.get_paginated_response(
            [{"value": t.name, "label": t.name} for t in page]
        )

    @throttle_action((MakeRequestThrottle,))
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        data = {"status": "success", "url": instance.get_absolute_domain_url()}
        headers = {"Location": str(instance.get_absolute_url())}
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user, request=self.request)
