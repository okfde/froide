from django.contrib.auth import get_user_model

from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from ..auth import (
    CreateOnlyWithScopePermission,
    get_read_foiattachment_queryset,
)
from ..models import FoiAttachment
from ..serializers import (
    FoiAttachmentSerializer,
    FoiAttachmentTusSerializer,
    FoiRequestListSerializer,
)

User = get_user_model()


class FoiAttachmentFilter(filters.FilterSet):
    class Meta:
        model = FoiAttachment
        fields = (
            "name",
            "filetype",
            "approved",
            "is_redacted",
            "belongs_to",
        )


class FoiAttachmentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_action_classes = {
        "create": FoiAttachmentTusSerializer,
        "list": FoiAttachmentSerializer,
        "retrieve": FoiAttachmentSerializer,
    }
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FoiAttachmentFilter
    permission_classes = (CreateOnlyWithScopePermission,)
    required_scopes = ["upload:message"]

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return FoiRequestListSerializer

    def get_queryset(self):
        qs = get_read_foiattachment_queryset(self.request)
        return self.optimize_query(qs)

    def optimize_query(self, qs):
        return qs.prefetch_related(
            "belongs_to",
            "belongs_to__request",
            "belongs_to__request__user",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        data = FoiAttachmentSerializer(instance, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        return serializer.save()
