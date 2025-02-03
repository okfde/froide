from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from ..auth import (
    CreateOnlyWithScopePermission,
    get_read_foiattachment_queryset,
)
from ..models import FoiAttachment
from ..permissions import WriteFoiRequestPermission
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
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_action_classes = {
        "create": FoiAttachmentTusSerializer,
        "list": FoiAttachmentSerializer,
        "retrieve": FoiAttachmentSerializer,
        "delete": FoiAttachmentSerializer,
    }
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FoiAttachmentFilter
    permission_classes = [
        CreateOnlyWithScopePermission,
        WriteFoiRequestPermission,
    ]
    required_scopes = ["make:message"]

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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if not instance.can_delete:
            return Response(
                data={"detail": _("Can't delete this attachment.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
