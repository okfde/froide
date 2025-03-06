from typing import override

from django.db.models import Prefetch
from django.utils import timezone
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.views import PermissionDenied
from taggit.serializers import TaggitSerializer, TagListSerializerField

from froide.document.api_views import DocumentSerializer
from froide.helper.text_diff import get_differences
from froide.publicbody.models import PublicBody
from froide.publicbody.serializers import (
    FoiLawSerializer,
    LawRelatedField,
    PublicBodyRelatedField,
    PublicBodySerializer,
    SimplePublicBodySerializer,
)
from froide.upload.fields import UploadRelatedField

from .auth import (
    can_moderate_pii_foirequest,
    can_read_foirequest_authenticated,
    can_write_foirequest,
    get_read_foiattachment_queryset,
)
from .fields import (
    FoiAttachmentRelatedField,
    FoiMessageRelatedField,
    FoiRequestCostsField,
    FoiRequestRelatedField,
)
from .models import FoiAttachment, FoiEvent, FoiMessage, FoiRequest
from .models.message import (
    MESSAGE_KIND_USER_ALLOWED,
    FoiMessageDraft,
)
from .models.request import USER_ALLOWED_STATUS
from .services import CreateRequestService
from .utils import postal_date
from .validators import clean_reference


class FoiRequestListSerializer(
    TaggitSerializer, serializers.HyperlinkedModelSerializer
):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:request-detail", lookup_field="pk"
    )
    public_body = SimplePublicBodySerializer(read_only=True)
    law = LawRelatedField()
    jurisdiction = serializers.HyperlinkedRelatedField(
        view_name="api:jurisdiction-detail", lookup_field="pk", read_only=True
    )
    same_as = serializers.HyperlinkedRelatedField(
        view_name="api:request-detail", lookup_field="pk", read_only=True
    )
    user = serializers.SerializerMethodField(source="get_user")
    status = serializers.ChoiceField(choices=USER_ALLOWED_STATUS)

    # TODO: change to hyperlinked field
    project = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )
    campaign = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="api:campaign-detail", lookup_field="pk"
    )
    tags = TagListSerializerField()

    description = serializers.CharField(source="get_description")
    redacted_description = serializers.SerializerMethodField()
    refusal_reason = serializers.CharField()
    costs = FoiRequestCostsField()

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
        read_only_fields = (
            "is_foi",
            "checked",
            "public",
            "same_as_count",
            "same_as",
            "due_date",
            "resolved_on",
            "last_message",
            "created_at",
            "last_modified_at",
            "public_body",
            "slug",
            "title",
            "reference",
            "user",
            "project",  # TODO: make this updatable
            "campaign",
        )

    def validate_status(self, value):
        if value not in USER_ALLOWED_STATUS:
            raise serializers.ValidationError(
                _("Choose a valid status: %s") % ", ".join(USER_ALLOWED_STATUS)
            )
        return value

    def validate_refusal_reson(self, value):
        request = self.context.get("request", None)

        if request:
            foirequest = request.object
            if foirequest.law:
                keys = [item[0] for item in foirequest.law.get_refusal_reason_choices()]

                if value not in keys:
                    raise serializers.ValidationError(
                        "The refusal reason doesn't apply to the law."
                    )

        return value

    def get_user(self, obj):
        if obj.user is None:
            return None
        request = self.context["request"]
        user = request.user
        if obj.user == user or can_moderate_pii_foirequest(obj, request):
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

    @override
    def update(self, instance, validated_data):
        user = self.context["request"].user

        if "costs" in validated_data:
            FoiRequest.costs_reported.send(
                sender=instance, user=user, costs=validated_data["costs"]
            )

        if (
            "status" in validated_data
            or "resolution" in validated_data
            or "refusal_reason" in validated_data
        ):
            previous_status = instance.status
            previous_resolution = instance.resolution

            FoiRequest.status_changed.send(
                sender=instance,
                user=user,
                status=validated_data.get("status"),
                resolution=validated_data.get("resolution"),
                previous_status=previous_status,
                previous_resolution=previous_resolution,
                data={
                    "costs": validated_data.get("costs", instance.costs),
                    "refusal_reason": validated_data.get("refusal_reason"),
                },
            )

        return super().update(instance, validated_data)


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
    resource_uri = serializers.HyperlinkedIdentityField(view_name="api:message-detail")
    request = FoiRequestRelatedField(read_only=True)
    attachments = serializers.SerializerMethodField(source="get_attachments")
    sender_public_body = PublicBodyRelatedField(required=False, allow_null=True)
    recipient_public_body = PublicBodyRelatedField(required=False, allow_null=True)

    subject = serializers.SerializerMethodField(source="get_subject")
    content = serializers.SerializerMethodField(source="get_content")
    redacted_subject = serializers.SerializerMethodField(source="get_redacted_subject")
    redacted_content = serializers.SerializerMethodField(source="get_redacted_content")
    url = serializers.CharField(source="get_absolute_domain_url", read_only=True)
    status = serializers.ChoiceField(
        choices=FoiRequest.STATUS.choices,
        required=False,
        allow_blank=True,
        read_only=True,
    )
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = FoiMessage
        depth = 0
        fields = [
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
            "registered_mail_date",
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
        ]
        read_only_fields = [
            "sent",
            "is_response",
            "kind",
            "is_escalation",
            "content_hidden",
            "is_draft",
            "not_publishable",
            "last_modified_at",
        ]

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

    def validate_kind(self, value):
        # forbid users from e.g. creating a fake e-mail message
        if value not in MESSAGE_KIND_USER_ALLOWED:
            raise serializers.ValidationError(
                _("This message kind can not be created via the API.")
            )
        return value

    def validate_request(self, value):
        if not can_write_foirequest(value, self.context["request"]):
            raise PermissionDenied(
                _("You do not have permission to add a message to this request.")
            )
        return value

    def validate_timestamp(self, value):
        # this handles updating FoiMessages
        # when creating a FoiMessageDraft, the timestamp is set correctly when publishing

        now = timezone.now()
        if value > now:
            raise ValidationError(
                _("The timestamp is in the future, that is not possible.")
            )

        if self.instance and self.instance.is_postal:
            return postal_date(self.instance, value)
        return value

    def validate_registered_mail_date(self, value):
        return self.validate_timestamp(value)

    def validate(self, attrs):
        timestamp = attrs.get("timestamp") or self.instance.timestamp
        foirequest = attrs.get("request") or self.instance.request

        if timestamp < foirequest.created_at:
            raise ValidationError(
                _("Your message date is before the request was made.")
            )

        # TODO: find a better solution for this
        sender_public_body = attrs.get(
            "sender_public_body",
            self.instance.sender_public_body if self.instance else None,
        )
        recipient_public_body = attrs.get(
            "recipient_public_body",
            self.instance.recipient_public_body if self.instance else None,
        )
        is_response = attrs.get(
            "is_response", self.instance.is_response if self.instance else None
        )

        if is_response is None:
            raise ValidationError(_("is_response is required"))
        elif is_response:
            if sender_public_body is None or recipient_public_body is not None:
                raise ValidationError(
                    _(
                        "Response messages must have a sender public body, no sender user and no recipient public body."
                    )
                )
        else:
            if sender_public_body is not None or recipient_public_body is None:
                raise ValidationError(
                    _(
                        "Non-response messages must have a recipent public body, but no sender public body."
                    )
                )

        return super().validate(attrs)

    @override
    def update(self, instance, validated_data):
        if not instance.is_draft and len(validated_data) != 0:
            request = self.context["request"]
            FoiEvent.objects.create_event(
                FoiEvent.EVENTS.MESSAGE_EDITED,
                instance.request,
                message=instance,
                user=request.user,
                context=validated_data,
            )

        return super().update(instance, validated_data)


class FoiMessageDraftSerializer(FoiMessageSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:message-draft-detail"
    )
    request = FoiRequestRelatedField()
    timestamp = serializers.DateTimeField(default=timezone.now)

    class Meta(FoiMessageSerializer.Meta):
        model = FoiMessageDraft
        read_only_fields = [
            "sent",
            "is_escalation",
            "content_hidden",
            "is_draft",
            "not_publishable",
            "timestamp",
            "last_modified_at",
        ]


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
    belongs_to = FoiMessageRelatedField(read_only=True)
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
            "can_change_approval",
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
    message = FoiMessageRelatedField()
    upload = UploadRelatedField()


class ImageAttachmentConverterItemSerializer(serializers.Serializer):
    attachment = FoiAttachmentRelatedField(
        queryset=FoiAttachment.objects.filter(filetype__startswith="image/"),
        error_messages={
            "does_not_exist": _("Attachment does not exist or is not an image.")
        },
    )
    rotate = serializers.IntegerField(default=0, max_value=360, min_value=0)


class ImageAttachmentConverterSerializer(serializers.Serializer):
    title = serializers.CharField(default=_("Letter"), required=False)
    images = ImageAttachmentConverterItemSerializer(many=True)
    message = FoiMessageRelatedField()


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
