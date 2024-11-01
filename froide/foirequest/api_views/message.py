from django.contrib.auth import get_user_model

from django_filters import rest_framework as filters
from rest_framework import viewsets

from ..auth import (
    get_read_foimessage_queryset,
)
from ..models import FoiMessage
from ..serializers import FoiMessageSerializer, optimize_message_queryset

User = get_user_model()


class FoiMessageFilter(filters.FilterSet):
    class Meta:
        model = FoiMessage
        fields = (
            "request",
            "kind",
            "is_response",
        )


class FoiMessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FoiMessageSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FoiMessageFilter

    def get_queryset(self):
        qs = get_read_foimessage_queryset(self.request).order_by()
        return self.optimize_query(qs)

    def optimize_query(self, qs):
        return optimize_message_queryset(self.request, qs)

    # @action(methods=["get", "post"], detail=False, url_name="draft")
    # def get_or_create_draft(self, request):
