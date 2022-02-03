from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from froide.foirequest.auth import is_foirequest_moderator
from froide.foirequest.models import FoiRequest

from .models import ProblemReport


def get_problem_reports(request):
    extra_filter = {}
    if not request.user.has_perm("foirequest.see_private"):
        extra_filter.update(
            {"message__request__visibility": FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC}
        )

    return ProblemReport.objects.filter(
        resolved=False, escalated__isnull=True, **extra_filter
    ).select_related("message")


class ProblemReportSerializer(serializers.HyperlinkedModelSerializer):
    kind_label = serializers.SerializerMethodField(
        source="get_kind_label", read_only=True
    )
    message_subject = serializers.SerializerMethodField(
        source="get_message_subject", read_only=True
    )
    message_url = serializers.SerializerMethodField(
        source="get_message_url", read_only=True
    )

    class Meta:
        model = ProblemReport
        fields = (
            "id",
            "message_id",
            "kind",
            "kind_label",
            "message_subject",
            "message_url",
            "timestamp",
            "auto_submitted",
            "resolved",
            "resolved",
            "description",
            "resolution",
            "resolution_timestamp",
            "claimed",
            "related_publicbody_id",
            "escalated",
            "moderator_id",
            "is_requester",
        )

    def get_kind_label(self, obj):
        return obj.get_kind_display()

    def get_message_subject(self, obj):
        return obj.message.subject

    def get_message_url(self, obj):
        return obj.message.get_absolute_domain_short_url()


class ResolutionSerializer(serializers.Serializer):
    resolution = serializers.CharField(allow_blank=True)


class EscalationSerializer(serializers.Serializer):
    escalation = serializers.CharField(allow_blank=True)


class ModeratorPermission(BasePermission):
    def has_permission(self, request, view):
        return is_foirequest_moderator(request)


class ProblemReportViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (ModeratorPermission,)

    serializer_action_classes = {}

    def get_queryset(self):
        return get_problem_reports(self.request)

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return ProblemReportSerializer

    @action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        problem = self.get_object()
        if problem.moderator is None:
            problem.claim(request.user)
            return Response({"status": "claimed"})
        return Response(
            {"error": "already claimed"}, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=["post"])
    def unclaim(self, request, pk=None):
        problem = self.get_object()
        if problem.moderator == request.user:
            problem.unclaim(request.user)
            return Response({"status": "unclaimed"})
        return Response(
            {"error": "already claimed"}, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        problem = self.get_object()
        serializer = ResolutionSerializer(data=request.data)
        if serializer.is_valid():
            problem.resolve(request.user, resolution=serializer.data["resolution"])
            return Response({"status": "resolved"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        problem = self.get_object()
        serializer = EscalationSerializer(data=request.data)
        if serializer.is_valid() and not problem.escalated:
            problem.escalate(request.user, escalation=serializer.data["escalation"])
            return Response({"status": "escalated"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
