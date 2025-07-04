from functools import partial
from typing import override

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from froide.campaign.models import Campaign
from froide.document.api_views import DocumentSerializer
from froide.foirequest.models.message import FoiMessage
from froide.helper.auth import is_crew
from froide.helper.storage import make_unique_filename
from froide.helper.text_utils import slugify
from froide.publicbody.models import PublicBody

from ..auth import (
    CreateOnlyWithScopePermission,
    get_read_foiattachment_queryset,
    get_read_foimessage_queryset,
)
from ..models import FoiAttachment, FoiEvent
from ..permissions import WriteFoiRequestPermission
from ..serializers import (
    FoiAttachmentSerializer,
    FoiAttachmentTusSerializer,
    ImageAttachmentConverterSerializer,
)
from ..tasks import convert_images_to_pdf_api_task, move_upload_to_attachment

User = get_user_model()


class FoiAttachmentFilter(filters.FilterSet):
    belongs_to = filters.ModelChoiceFilter(
        queryset=FoiMessage.objects.none(),
        field_name="belongs_to",
    )
    campaign = filters.ModelChoiceFilter(
        queryset=Campaign.objects.get_filter_list(),
        to_field_name="slug",
        null_value="-",
        empty_label=_("all/no campaigns"),
        null_label=_("no campaign"),
        method="filter_campaign",
    )
    publicbody = filters.ModelMultipleChoiceFilter(
        queryset=PublicBody._default_manager.all(),
        method="filter_publicbody",
    )

    class Meta:
        model = FoiAttachment
        fields = (
            "name",
            "filetype",
            "approved",
            "is_redacted",
            "belongs_to",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get("request")
        if request is None:
            request = self.view.request
        self.filters["belongs_to"].queryset = get_read_foimessage_queryset(
            request, FoiMessage.with_drafts.all()
        ).order_by()

    def filter_publicbody(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(belongs_to__request__public_body__in=value)

    def filter_campaign(self, qs, name, value):
        if value == "-":
            return qs.filter(belongs_to__request__campaign=None)
        return qs.filter(belongs_to__request__campaign=value)


class FoiAttachmentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = FoiAttachmentSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FoiAttachmentFilter
    permission_classes = [
        CreateOnlyWithScopePermission,
        WriteFoiRequestPermission,
    ]
    required_scopes = ["write:attachment"]

    def get_serializer_class(self):
        if self.action == "create":
            return FoiAttachmentTusSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        qs = get_read_foiattachment_queryset(self.request)
        return self.optimize_query(qs)

    def optimize_query(self, qs):
        return qs.prefetch_related(
            "belongs_to",
            "belongs_to__request",
            "document",
        )

    @extend_schema(
        request=FoiAttachmentTusSerializer,
        responses={status.HTTP_201_CREATED: FoiAttachmentSerializer},
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
            request=request,
            **{"added": str(att)},
        )

        data = FoiAttachmentSerializer(att, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)

    @override
    def perform_destroy(self, instance):
        instance.remove_file_and_delete()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        message = instance.belongs_to

        if not message.is_postal:
            return Response(
                data={"detail": _("Can't delete attachments on non-postal messages.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not instance.can_delete:
            return Response(
                data={"detail": _("Can't delete this attachment.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.attachment_deleted.send(
            sender=instance,
            request=request,
        )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update_approval(self, request, approve: bool):
        instance = self.get_object()

        if instance.can_change_approval:
            event_name = (
                FoiEvent.EVENTS.ATTACHMENT_DEPUBLISHED
                if instance.approved
                else FoiEvent.EVENTS.ATTACHMENT_APPROVED
            )

            instance.approve_and_save(approve)

            FoiEvent.objects.create_event(
                event_name,
                instance.belongs_to.request,
                request=request,
                message=instance.belongs_to,
                attachment_id=instance.pk,
            )

            return Response(
                FoiAttachmentSerializer(instance, context={"request": request}).data
            )
        else:
            return Response(
                status=status.HTTP_403_FORBIDDEN,
                data={"detail": _("Can't approve this attachment.")},
            )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk):
        return self.update_approval(request, approve=True)

    @action(detail=True, methods=["post"])
    def unapprove(self, request, pk):
        return self.update_approval(request, approve=False)

    @extend_schema(responses={status.HTTP_201_CREATED: DocumentSerializer})
    @action(detail=True, methods=["post"])
    def to_document(self, request, pk=None):
        att = self.get_object()

        if not att.can_approve and not is_crew(request.user):
            return Response(
                {"detail": _("You can't convert this attachment to a document.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        if att.redacted:
            return Response(
                {
                    "detail": _(
                        "Only the redacted version of this attachment can be converted to a document."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if att.document is not None:
            return Response(
                {
                    "detail": _(
                        "This attachment has already been converted to a document."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not att.is_pdf:
            return Response(
                {"detail": _("Only PDF attachments can be converted to a document.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc = att.create_document()
        att.document_created.send(
            sender=att,
            request=request,
        )

        data = DocumentSerializer(doc, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={status.HTTP_201_CREATED: FoiAttachmentSerializer},
        operation_id="convert_images_to_pdf",
    )
    @action(
        detail=False,
        methods=["post"],
        serializer_class=ImageAttachmentConverterSerializer,
    )
    def convert_to_pdf(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            message = serializer.validated_data["message"]
            foirequest = message.request

            attachments = [i["attachment"] for i in serializer.validated_data["images"]]

            if not all(a.belongs_to == message for a in attachments):
                return Response(
                    {
                        "images": [
                            _("All attachments need to belong to the provided message.")
                        ]
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if len(attachments) != len(set(attachments)):
                return Response(
                    {"images": [_("Images must not be duplicated.")]},
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
