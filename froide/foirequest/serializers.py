from django.db.models import Prefetch

from rest_framework import serializers

from froide.document.api_views import DocumentSerializer
from froide.foirequest.forms.message import TransferUploadForm
from froide.foirequest.models.message import MessageKind
from froide.helper.auth import get_write_queryset
from froide.helper.text_diff import get_differences
from froide.publicbody.api_views import (
    FoiLawSerializer,
    PublicBodySerializer,
    SimplePublicBodySerializer,
)
from froide.publicbody.models import PublicBody

from .auth import (
    can_read_foirequest_authenticated,
    get_read_foiattachment_queryset,
)
from .models import FoiAttachment, FoiMessage, FoiRequest
from .services import CreateRequestService
from .validators import clean_reference


class TagListField(serializers.CharField):
    child = serializers.CharField()

    def to_representation(self, data):
        return [t.name for t in data.all()]


class FoiRequestListSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:request-detail", lookup_field="pk"
    )
    public_body = SimplePublicBodySerializer(read_only=True)
    law = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:law-detail", lookup_field="pk"
    )
    jurisdiction = serializers.HyperlinkedRelatedField(
        view_name="api:jurisdiction-detail", lookup_field="pk", read_only=True
    )
    same_as = serializers.HyperlinkedRelatedField(
        view_name="api:request-detail", lookup_field="pk", read_only=True
    )
    user = serializers.SerializerMethodField(source="get_user")
    project = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )
    campaign = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:campaign-detail", lookup_field="pk"
    )
    tags = TagListField()

    description = serializers.CharField(source="get_description")
    redacted_description = serializers.SerializerMethodField()
    costs = serializers.SerializerMethodField()

    class Meta:
        model = FoiRequest
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "url",
            "jurisdiction",
            "is_foi",
            "checked",
            "refusal_reason",
            "costs",
            "public",
            "law",
            "description",
            "redacted_description",
            "summary",
            "same_as_count",
            "same_as",
            "due_date",
            "resolved_on",
            "last_message",
            "created_at",
            "last_modified_at",
            "status",
            "public_body",
            "resolution",
            "slug",
            "title",
            "reference",
            "user",
            "project",
            "campaign",
            "tags",
        )

    def get_user(self, obj):
        if obj.user is None:
            return None
        user = self.context["request"].user
        if obj.user == user or user.is_superuser:
            return obj.user.pk
        if obj.user.private:
            return None
        return obj.user.pk

    def get_redacted_description(self, obj):
        request = self.context["request"]
        authenticated_read = can_read_foirequest_authenticated(
            obj, request, allow_code=False
        )
        return obj.get_redacted_description(authenticated_read)

    def get_costs(self, obj):
        return float(obj.costs)


class FoiRequestDetailSerializer(FoiRequestListSerializer):
    public_body = PublicBodySerializer(read_only=True)
    law = FoiLawSerializer(read_only=True)
    messages = serializers.SerializerMethodField()

    class Meta(FoiRequestListSerializer.Meta):
        fields = FoiRequestListSerializer.Meta.fields + ("messages",)

    def get_messages(self, obj):
        qs = optimize_message_queryset(
            self.context["request"], FoiMessage.objects.filter(request=obj)
        )
        return FoiMessageSerializer(
            qs, read_only=True, many=True, context=self.context
        ).data


class MakeRequestSerializer(serializers.Serializer):
    publicbodies = serializers.PrimaryKeyRelatedField(
        queryset=PublicBody.objects.all(), many=True
    )

    subject = serializers.CharField(max_length=230)
    body = serializers.CharField()

    full_text = serializers.BooleanField(required=False, default=False)
    public = serializers.BooleanField(required=False, default=True)
    reference = serializers.CharField(required=False, default="")
    tags = serializers.ListField(
        required=False, child=serializers.CharField(max_length=255)
    )

    def validate_reference(self, value):
        cleaned_reference = clean_reference(value)
        if value and cleaned_reference != value:
            raise serializers.ValidationError("Reference not clean")
        return cleaned_reference

    def create(self, validated_data):
        service = CreateRequestService(validated_data)
        return service.execute(validated_data["request"])


class FoiMessageSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:message-detail", lookup_field="pk"
    )
    request = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:request-detail"
    )
    attachments = serializers.SerializerMethodField(source="get_attachments")
    sender_public_body = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:publicbody-detail"
    )
    recipient_public_body = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:publicbody-detail"
    )

    subject = serializers.SerializerMethodField(source="get_subject")
    content = serializers.SerializerMethodField(source="get_content")
    redacted_subject = serializers.SerializerMethodField(source="get_redacted_subject")
    redacted_content = serializers.SerializerMethodField(source="get_redacted_content")
    sender = serializers.CharField()
    url = serializers.CharField(source="get_absolute_domain_url")
    status_name = serializers.CharField(source="get_status_display")

    class Meta:
        model = FoiMessage
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "url",
            "request",
            "sent",
            "is_response",
            "is_postal",
            "is_draft",
            "kind",
            "is_escalation",
            "content_hidden",
            "sender_public_body",
            "recipient_public_body",
            "status",
            "timestamp",
            "redacted",
            "not_publishable",
            "attachments",
            "subject",
            "content",
            "redacted_subject",
            "redacted_content",
            "sender",
            "status_name",
            "last_modified_at",
        )

    def _is_authenticated_read(self, obj):
        request = self.context["request"]
        return can_read_foirequest_authenticated(obj.request, request, allow_code=False)

    def get_subject(self, obj):
        if obj.content_hidden and not self._is_authenticated_read(obj):
            return ""
        return obj.get_subject()

    def get_content(self, obj):
        if obj.content_hidden and not self._is_authenticated_read(obj):
            return ""
        return obj.get_content()

    def get_redacted_subject(self, obj):
        if self._is_authenticated_read(obj):
            show, hide = obj.subject, obj.subject_redacted
        else:
            if obj.content_hidden:
                return []
            show, hide = obj.subject_redacted, obj.subject
        return list(get_differences(show, hide))

    def get_redacted_content(self, obj):
        authenticated_read = self._is_authenticated_read(obj)
        if obj.content_hidden and not authenticated_read:
            return []
        return obj.get_redacted_content(authenticated_read)

    def get_attachments(self, obj):
        if not hasattr(obj, "visible_attachments"):
            obj.visible_attachments = get_read_foiattachment_queryset(
                self.context["request"],
                queryset=FoiAttachment.objects.filter(belongs_to=obj),
            ).prefetch_related("belongs_to", "document", "converted", "redacted")

        serializer = FoiAttachmentSerializer(
            obj.visible_attachments,  # already filtered by prefetch
            many=True,
            context={"request": self.context["request"]},
        )
        return serializer.data


class FoiAttachmentSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:attachment-detail", lookup_field="pk"
    )
    converted = serializers.HyperlinkedRelatedField(
        view_name="api:attachment-detail",
        lookup_field="pk",
        read_only=True,
    )
    redacted = serializers.HyperlinkedRelatedField(
        view_name="api:attachment-detail",
        lookup_field="pk",
        read_only=True,
    )
    belongs_to = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:message-detail"
    )
    document = DocumentSerializer()
    site_url = serializers.CharField(source="get_absolute_domain_url", read_only=True)
    anchor_url = serializers.CharField(source="get_domain_anchor_url", read_only=True)
    file_url = serializers.SerializerMethodField(source="get_file_url", read_only=True)

    class Meta:
        model = FoiAttachment
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "belongs_to",
            "name",
            "filetype",
            "size",
            "site_url",
            "anchor_url",
            "file_url",
            "pending",
            "is_converted",
            "converted",
            "approved",
            "can_approve",
            "redacted",
            "is_redacted",
            "can_redact",
            "can_delete",
            "is_pdf",
            "is_image",
            "is_irrelevant",
            "document",
        )

    def get_file_url(self, obj):
        return obj.get_absolute_domain_file_url(authorized=True)


class FoiAttachmentTusSerializer(serializers.Serializer):
    message = serializers.IntegerField()
    upload = serializers.CharField()

    def validate_message(self, value):
        writable_requests = get_write_queryset(
            FoiRequest.objects.all(),
            self.context["request"],
            has_team=True,
            scope="upload:message",
        )
        try:
            return FoiMessage.objects.get(
                pk=value,
                request__in=writable_requests,
                kind=MessageKind.POST,
            )
        except FoiMessage.DoesNotExist as e:
            raise serializers.ValidationError("Message not found") from e

    def validate(self, data):
        self.form = TransferUploadForm(
            data=data, foimessage=data["message"], user=self.context["request"].user
        )
        if not self.form.is_valid():
            raise serializers.ValidationError("Invalid upload")

        return data

    def create(self, validated_data):
        added = self.form.save(self.context["request"])
        return added[0]


def optimize_message_queryset(request, qs):
    atts = get_read_foiattachment_queryset(
        request, queryset=FoiAttachment.objects.filter(belongs_to__in=qs)
    ).prefetch_related("belongs_to", "document", "converted", "redacted")
    return qs.prefetch_related(
        "request",
        "request__user",
        "sender_user",
        "sender_public_body",
        Prefetch("foiattachment_set", queryset=atts, to_attr="visible_attachments"),
    )
