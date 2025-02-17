from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..auth import (
    get_read_foimessage_queryset,
)
from ..models import FoiMessage, FoiMessageDraft, FoiRequest
from ..permissions import WriteFoiRequestPermission
from ..serializers import (
    FoiMessageDraftSerializer,
    FoiMessageSerializer,
    optimize_message_queryset,
)

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
    serializer_class = FoiMessageSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FoiMessageFilter
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        WriteFoiRequestPermission,
    ]

    def optimize_query(self, qs):
        return optimize_message_queryset(self.request, qs)

    def get_queryset(self):
        qs = get_read_foimessage_queryset(self.request).order_by()
        return self.optimize_query(qs)


class FoiMessageDraftViewSet(
    FoiMessageViewSet,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    serializer_class = FoiMessageDraftSerializer
    filterset_class = FoiMessageDraftFilter
    required_scopes = ["write:message"]

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
