from functools import partial

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from froide.helper.storage import make_unique_filename
from froide.helper.text_utils import slugify

from ..auth import (
    get_read_foimessage_queryset,
)
from ..models import FoiAttachment, FoiMessage, FoiMessageDraft, FoiRequest
from ..permissions import WriteFoiRequestPermission
from ..serializers import (
    FoiAttachmentConvertImageSerializer,
    FoiAttachmentSerializer,
    FoiMessageDraftSerializer,
    FoiMessageSerializer,
    optimize_message_queryset,
)
from ..tasks import convert_images_to_pdf_api_task

User = get_user_model()


class FoiMessageFilter(filters.FilterSet):
    class Meta:
        model = FoiMessage
        fields = ("request", "kind", "is_response")


class FoiMessageDraftFilter(filters.FilterSet):
    class Meta:
        model = FoiMessageDraft
        fields = ("request",)


class FoiMessageViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FoiMessageFilter
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        WriteFoiRequestPermission,
    ]

    def get_queryset(self):
        qs = get_read_foimessage_queryset(self.request).order_by()
        return self.optimize_query(qs)

    def optimize_query(self, qs):
        return optimize_message_queryset(self.request, qs)

    def get_serializer_class(self):
        if self.action == "convert_to_pdf":
            return FoiAttachmentConvertImageSerializer
        return FoiMessageSerializer

    @action(detail=True, methods=["post"])
    def convert_to_pdf(self, request, pk=None):
        message = self.get_object()
        foirequest = message.request

        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            attachments = [i["attachment"] for i in serializer.validated_data["images"]]

            if not all(a.belongs_to == message for a in attachments):
                return Response(
                    {"images": [_("Attachment does not exist on this message.")]},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if len(attachments) != len(set(attachments)):
                return Response(
                    {"images": [_("Images must be unique.")]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            title = serializer.validated_data["title"]
            existing_names = {a.name for a in message.attachments}

            name = "{}.pdf".format(slugify(title))
            name = make_unique_filename(name, existing_names)

            can_approve = not foirequest.not_publishable
            target = FoiAttachment.objects.create(
                name=name,
                belongs_to=message,
                approved=False,
                filetype="application/pdf",
                is_converted=True,
                can_approve=can_approve,
            )

            FoiAttachment.objects.filter(id__in=[a.id for a in attachments]).update(
                converted_id=target.id, can_approve=False, approved=False
            )
            instructions = [
                {"rotate": i["rotate"]} for i in serializer.validated_data["images"]
            ]

            transaction.on_commit(
                partial(
                    convert_images_to_pdf_api_task.delay,
                    attachments,
                    target,
                    instructions,
                    can_approve=can_approve,
                )
            )

            return Response(
                FoiAttachmentSerializer(target, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FoiMessageDraftViewSet(
    FoiMessageViewSet,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    serializer_class = FoiMessageDraftSerializer
    filterset_class = FoiMessageDraftFilter
    required_scopes = ["make:message"]
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        WriteFoiRequestPermission,
    ]

    def get_queryset(self):
        qs = get_read_foimessage_queryset(
            self.request, queryset=FoiMessageDraft.objects.all()
        ).order_by()
        return self.optimize_query(qs)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        message = self.get_object()
        message.is_draft = False

        if not message.is_response:
            message.sender_user = request.user

        if not message.can_be_published():
            if message.is_response:
                error_message = _(
                    "Response messages must have a sender public body, no sender user and no recipient public body."
                )
            else:
                error_message = _(
                    "Non-response messages must have a recipent public body, but no sender public body."
                )

            return Response({"detail": error_message}, status=400)

        message.save()

        if message.is_response:
            FoiRequest.message_received.send(
                sender=message.request, message=message, user=request.user
            )
        else:
            FoiRequest.message_sent.send(
                sender=message.request, message=message, user=request.user
            )

        # return it as a regular message
        serializer = FoiMessageSerializer(
            message, context=self.get_serializer_context()
        )
        return Response(serializer.data)
