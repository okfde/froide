from functools import partial

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from ..auth import (
    CreateOnlyWithScopePermission,
    get_read_foiattachment_queryset,
)
from ..models import FoiAttachment, FoiEvent
from ..permissions import WriteFoiRequestPermission
from ..serializers import (
    FoiAttachmentSerializer,
    FoiAttachmentTusSerializer,
    FoiRequestListSerializer,
)
from ..tasks import move_upload_to_attachment

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

        upload = serializer.validated_data["upload"]
        foimessage = serializer.validated_data["message"]

        att = FoiAttachment(belongs_to=foimessage, name=upload.filename)
        att.size = upload.size
        att.filetype = upload.content_type
        att.pending = True  # file needs to be moved by task
        att.can_approve = not foimessage.request.not_publishable
        att.save()

        foimessage._attachments = None
        upload.ensure_saving()
        upload.save()

        transaction.on_commit(
            partial(move_upload_to_attachment.delay, att.id, upload.id)
        )

        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.ATTACHMENT_UPLOADED,
            foimessage.request,
            message=foimessage,
            user=request.user,
            **{"added": str(att)},
        )

        data = FoiAttachmentSerializer(att, context={"request": request}).data
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
