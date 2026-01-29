from django.contrib.auth import get_user_model

from django_filters import rest_framework as filters
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from froide.foirequest.utils import postal_date

from ..auth import (
    get_read_foimessage_queryset,
    get_write_foimessage_queryset,
)
from ..models import FoiMessage, FoiRequest
from ..permissions import (
    OnlyPostalMessagesWritable,
    WriteFoiRequestPermission,
    WriteMessageScopePermission,
)
from ..serializers import (
    FoiMessageSerializer,
    optimize_message_queryset,
)

User = get_user_model()


class FoiMessageFilter(filters.FilterSet):
    class Meta:
        model = FoiMessage
        fields = ("request", "kind", "is_response", "is_draft")


class FoiMessageViewSet(
    mixins.UpdateModelMixin, mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet
):
    serializer_class = FoiMessageSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FoiMessageFilter
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        WriteFoiRequestPermission,
        WriteMessageScopePermission,
        OnlyPostalMessagesWritable,
    ]

    def optimize_query(self, qs):
        return optimize_message_queryset(self.request, qs)

    def get_queryset(self):
        qs = self.serializer_class.Meta.model.with_drafts.all()

        if self.request.method in permissions.SAFE_METHODS:
            qs = get_read_foimessage_queryset(self.request, qs).order_by()
        else:
            qs = get_write_foimessage_queryset(self.request, qs).order_by()
        return self.optimize_query(qs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message_data = serializer.validated_data.copy()
        foirequest = message_data.pop("request")
        kind = message_data.pop("kind")

        message, created = FoiMessage.with_drafts.update_or_create(
            request=foirequest,
            kind=kind,
            is_draft=True,
            defaults=message_data,
        )
        if created:
            response_status = status.HTTP_201_CREATED
        else:
            response_status = status.HTTP_200_OK

        serializer = FoiMessageSerializer(
            message, context=self.get_serializer_context()
        )
        return Response(serializer.data, status=response_status)

    @action(
        detail=True,
        methods=["post"],
    )
    def publish(self, request, pk=None):
        message = self.get_object()
        if not message.is_draft:
            return Response({"detail": "Message is not a draft"}, status=400)

        if not message.is_postal:
            return Response({"detail": "Message must be postal message"}, status=400)

        message.is_draft = False
        message.timestamp = postal_date(message)

        message.save()
        foirequest = message.request
        foirequest._messages = None

        if message.is_response:
            FoiRequest.message_received.send(
                sender=foirequest, message=message, user=request.user, request=request
            )
        else:
            FoiRequest.message_sent.send(
                sender=foirequest, message=message, user=request.user, request=request
            )

        # return it as a regular message
        serializer = FoiMessageSerializer(
            message, context=self.get_serializer_context()
        )
        return Response(serializer.data)
