import re
from io import BytesIO

from django import forms
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.views.main import ChangeList
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models.functions import RowNumber
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from froide.account.models import UserTag
from froide.guide.models import Action
from froide.guide.utils import assign_guidance_action
from froide.helper.admin_utils import (
    ForeignKeyFilter,
    MultiFilterMixin,
    SearchFilter,
    TaggitListFilter,
    make_batch_tag_action,
    make_choose_object_action,
    make_greaterzerofilter,
    make_nullfilter,
)
from froide.helper.csv_utils import dict_to_csv_stream, export_csv_response
from froide.helper.email_parsing import parse_email
from froide.helper.forms import get_fake_fk_form_class
from froide.helper.widgets import TagAutocompleteWidget
from froide.publicbody.models import FoiLaw

from .models import (
    DeferredMessage,
    DeliveryStatus,
    FoiAttachment,
    FoiEvent,
    FoiMessage,
    FoiProject,
    FoiRequest,
    MessageTag,
    PublicBodySuggestion,
    RequestDraft,
    TaggedFoiRequest,
    TaggedMessage,
)
from .widgets import AttachmentFileWidget

SUBJECT_REQUEST_ID = re.compile(r" \[#(\d+)\]")


def execute_assign_guidance_action_to_last_message(
    admin, request, queryset, action_obj
):
    from froide.guide.tasks import add_action_to_queryset_task

    last_message_ids = (
        FoiMessage.objects.filter(request__in=queryset)
        .annotate(
            _number=models.Window(
                expression=RowNumber(),
                partition_by=models.F("request_id"),
                order_by=models.F("timestamp").desc(),
            )
        )
        .order_by(models.F("_number"))
        .values_list("id", flat=True)[: queryset.count()]
    )

    add_action_to_queryset_task.delay(action_obj.id, list(last_message_ids))


assign_guidance_action_to_last_message = make_choose_object_action(
    Action,
    execute_assign_guidance_action_to_last_message,
    _("Choose guidance action to attach to last message..."),
)


def execute_assign_tag_to_foirequest_user(admin, request, queryset, action_obj):
    from froide.account.models import User

    users = User.objects.filter(foirequest__in=queryset).distinct()
    for user in users:
        user.tags.add(action_obj)


assign_tag_to_foirequest_user = make_choose_object_action(
    UserTag,
    execute_assign_tag_to_foirequest_user,
    _("Tag users of selected requests..."),
)


class FoiMessageInline(admin.StackedInline):
    model = FoiMessage
    raw_id_fields = (
        "request",
        "sender_user",
        "sender_public_body",
        "recipient_public_body",
        "original",
    )
    exclude = ("content_rendered_auth", "content_rendered_anon")


class FoiRequestAdminForm(forms.ModelForm):
    class Meta:
        model = FoiRequest
        fields = "__all__"
        widgets = {
            "tags": TagAutocompleteWidget(
                autocomplete_url=reverse_lazy("api:request-tags-autocomplete")
            ),
        }


class FoiRequestTagsFilter(TaggitListFilter):
    tag_class = TaggedFoiRequest


class FoiRequestChangeList(ChangeList):
    def get_results(self, *args, **kwargs):
        ret = super().get_results(*args, **kwargs)
        q = self.queryset.aggregate(
            user_count=models.Count("user", distinct=True),
        )
        self.user_count = q["user_count"]

        return ret


class LawRelatedFieldListFilter(admin.RelatedFieldListFilter):
    """
    This optimizes the query for the law filter
    """

    def field_choices(self, field, request, model_admin):
        return [
            (x.id, str(x))
            for x in FoiLaw.objects.all()
            .select_related("jurisdiction")
            .prefetch_related("translations")
        ]


class FoiRequestAdmin(admin.ModelAdmin):
    form = FoiRequestAdminForm

    prepopulated_fields = {"slug": ("title",)}
    inlines = [
        FoiMessageInline,
    ]
    list_display = (
        "title",
        "first_message",
        "secret_address",
        "request_page",
        "public_body",
        "status",
        "visibility",
    )
    list_filter = (
        "jurisdiction",
        "first_message",
        "last_message",
        "status",
        "resolution",
        "is_foi",
        "checked",
        "public",
        "visibility",
        "is_blocked",
        "not_publishable",
        "campaign",
        make_nullfilter("same_as", _("Has same request")),
        ("user", ForeignKeyFilter),
        ("public_body", ForeignKeyFilter),
        ("project", ForeignKeyFilter),
        make_greaterzerofilter("costs", _("Costs given")),
        ("law", LawRelatedFieldListFilter),
        "refusal_reason",
    )
    search_fields = ["title", "description", "secret_address", "reference"]
    ordering = ("-last_message",)
    date_hierarchy = "first_message"

    actions = [
        "mark_checked",
        "mark_not_foi",
        "mark_successfully_resolved",
        "mark_refused",
        "tag_all",
        "mark_same_as",
        "update_index",
        "confirm_request",
        "unpublish",
        "add_to_project",
        "unblock_request",
        "close_requests",
        "attach_guidance_to_last_message",
        "tag_users",
    ]
    attach_guidance_to_last_message = assign_guidance_action_to_last_message
    tag_users = assign_tag_to_foirequest_user

    raw_id_fields = (
        "same_as",
        "public_body",
        "user",
        "team",
        "project",
        "jurisdiction",
        "law",
    )
    save_on_top = True

    tag_all = make_batch_tag_action(
        autocomplete_url=reverse_lazy("api:request-tags-autocomplete")
    )

    def get_changelist(self, request):
        return FoiRequestChangeList

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related("public_body")
        return qs

    def request_page(self, obj):
        return format_html(
            '<a href="{}">{}</a>', obj.get_absolute_url(), _("request page")
        )

    def mark_checked(self, request, queryset):
        from .utils import update_foirequest_index

        rows_updated = queryset.update(checked=True)
        update_foirequest_index(queryset)
        self.message_user(
            request, _("%d request(s) successfully marked as checked." % rows_updated)
        )

    mark_checked.short_description = _("Mark selected requests as checked")

    def mark_not_foi(self, request, queryset):
        from .utils import update_foirequest_index

        rows_updated = queryset.update(
            is_foi=False,
            public=False,
            visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER,
        )
        update_foirequest_index(queryset)
        self.message_user(
            request, _("%d request(s) successfully marked as not FoI." % rows_updated)
        )

    mark_not_foi.short_description = _("Mark selected requests as not FoI")

    def mark_successfully_resolved(self, request, queryset):
        from .utils import update_foirequest_index

        rows_updated = queryset.update(
            status=FoiRequest.STATUS.RESOLVED,
            resolution=FoiRequest.RESOLUTION.SUCCESSFUL,
        )
        update_foirequest_index(queryset)
        self.message_user(
            request,
            _(
                "%d request(s) have been marked as successfully resolved."
                % rows_updated
            ),
        )

    mark_successfully_resolved.short_description = _("Mark successfully resolved")

    def mark_refused(self, request, queryset):
        from .utils import update_foirequest_index

        rows_updated = queryset.update(
            status=FoiRequest.STATUS.RESOLVED, resolution=FoiRequest.RESOLUTION.REFUSED
        )
        update_foirequest_index(queryset)
        self.message_user(
            request, _("%d request(s) have been marked as refused." % rows_updated)
        )

    mark_refused.short_description = _("Mark as refused")

    def update_index(self, request, queryset):
        from .utils import update_foirequest_index

        update_foirequest_index(queryset)
        self.message_user(
            request,
            _("%d request(s) will be updated in the search index." % queryset.count()),
        )

    update_index.short_description = _("Update search index")

    def mark_same_as(self, request, queryset):
        """
        Mark selected requests as same as the one we are choosing now.

        """
        from .utils import update_foirequest_index

        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        Form = get_fake_fk_form_class(FoiRequest, self.admin_site)
        # User has already chosen the other req
        if request.POST.get("obj"):
            f = Form(request.POST)
            if f.is_valid():
                req = f.cleaned_data["obj"]
                queryset.update(same_as=req)
                count = FoiRequest.objects.filter(same_as=req).count()
                FoiRequest.objects.filter(id=req.id).update(same_as_count=count)
                update_foirequest_index(queryset)
                self.message_user(
                    request, _("Successfully marked requests as identical.")
                )
                # Return None to display the change list page again.
                return None
        else:
            f = Form()

        context = {
            "opts": opts,
            "queryset": queryset,
            "media": self.media,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "form": f,
            "applabel": opts.app_label,
        }

        # Display the confirmation page
        return TemplateResponse(request, "foirequest/admin/mark_same_as.html", context)

    mark_same_as.short_description = _("Mark selected requests as identical to...")

    def confirm_request(self, request, queryset):
        from .services import ActivatePendingRequestService

        foirequest = queryset[0]
        if foirequest.status != FoiRequest.STATUS.AWAITING_USER_CONFIRMATION:
            self.message_user(request, _("Request not in correct state!"))
            return None
        self.message_user(request, _("Message send successfully!"))
        req_service = ActivatePendingRequestService({"foirequest": foirequest})
        foirequest = req_service.process(request=None)
        return None

    confirm_request.short_description = _("Confirm request if unconfirmed")

    def unpublish(self, request, queryset):
        from .utils import update_foirequest_index

        queryset.update(
            public=False, visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER
        )
        update_foirequest_index(queryset)
        self.message_user(request, _("Selected requests are now unpublished."))

    unpublish.short_description = _("Unpublish")

    def unblock_request(self, request, queryset):
        for req in queryset:
            mes = req.messages[0]
            mes.timestamp = timezone.now()
            if req.law:
                req.due_date = req.law.calculate_due_date()
            req.is_blocked = False
            req.first_message = mes.timestamp
            req.save()
            mes.save()
            mes.force_resend()

    unblock_request.short_description = _("Unblock requests and send first message")

    def close_requests(self, request, queryset):
        from .utils import update_foirequest_index

        queryset.update(closed=True)
        update_foirequest_index(queryset)

    close_requests.short_description = _("Close requests")

    def add_to_project(self, request, queryset):
        """
        Mark selected requests as same as the one we are choosing now.

        """
        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        queryset = queryset.filter(project__isnull=True)

        Form = get_fake_fk_form_class(FoiProject, self.admin_site)
        # User has already chosen the other req
        if request.POST.get("obj"):
            f = Form(request.POST)
            if f.is_valid():
                project = f.cleaned_data["obj"]
                project.add_requests(queryset)
                self.message_user(request, _("Successfully added requests to project."))
                # Return None to display the change list page again.
                return None
        else:
            f = Form()

        context = {
            "opts": opts,
            "queryset": queryset,
            "media": self.media,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "form": f,
            "applabel": opts.app_label,
        }

        # Display the confirmation page
        return TemplateResponse(
            request, "foirequest/admin/add_to_project.html", context
        )

    add_to_project.short_description = _("Add selected requests to project...")


class FoiAttachmentInline(admin.TabularInline):
    model = FoiAttachment
    raw_id_fields = ("redacted", "converted", "document")
    formfield_overrides = {
        models.FileField: {"widget": AttachmentFileWidget},
    }


class DeliveryStatusInline(admin.TabularInline):
    model = DeliveryStatus
    extra = 0
    max_num = 1
    min_num = 0
    raw_id_fields = ("message",)
    readonly_fields = ("retry_count", "log", "status", "last_update")


class MessageTagsFilter(MultiFilterMixin, TaggitListFilter):
    tag_class = TaggedMessage
    title = "Tags"
    parameter_name = "tags__slug"
    lookup_name = "__in"


class FoiMessageAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = (
        "subject",
        "timestamp",
        "message_page",
        "sender_email",
        "recipient_email",
        "is_response",
        "kind",
        "get_deliverystatus_display",
    )
    list_filter = (
        "kind",
        "is_response",
        "sent",
        "status",
        "deliverystatus__status",
        make_nullfilter("deliverystatus", _("Has delivery status")),
        "sender_user__is_active",
        "sender_user__is_blocked",
        "sender_user__is_deleted",
        "request__campaign",
        MessageTagsFilter,
        ("request__reference", SearchFilter),
        ("sender_public_body", ForeignKeyFilter),
        ("recipient_public_body", ForeignKeyFilter),
        ("request__user", ForeignKeyFilter),
        make_nullfilter("foiattachment_set", _("Has attachments")),
    )
    search_fields = ["subject", "sender_email", "recipient_email"]
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"
    raw_id_fields = (
        "request",
        "sender_user",
        "sender_public_body",
        "recipient_public_body",
        "original",
    )
    inlines = [
        DeliveryStatusInline,
        FoiAttachmentInline,
    ]
    exclude = ("content_rendered_auth", "content_rendered_anon")
    actions = [
        "check_delivery_status",
        "resend_messages",
        "run_guidance",
        "run_guidance_notify",
        "attach_guidance_action",
        "tag_all",
    ]

    tag_all = make_batch_tag_action()

    def get_urls(self):
        urls = super(FoiMessageAdmin, self).get_urls()
        my_urls = [
            path(
                "<int:pk>/resend-message/",
                self.admin_site.admin_view(self.resend_message),
                name="foirequest-foimessage-resend_message",
            ),
            path(
                "<int:pk>/download-eml/",
                self.admin_site.admin_view(self.download_eml),
                name="foirequest-foimessage-download_eml",
            ),
        ]
        return my_urls + urls

    def get_queryset(self, request):
        qs = super(FoiMessageAdmin, self).get_queryset(request)
        qs = qs.prefetch_related("deliverystatus")
        return qs

    def save_model(self, request, obj, form, change):
        if (
            "plaintext" in form.changed_data
            or "plaintext_redacted" in form.changed_data
        ):
            obj.clear_render_cache()
        super().save_model(request, obj, form, change)

    def message_page(self, obj):
        return format_html(
            '<a href="{}">{}</a>', obj.get_absolute_short_url(), _("on site")
        )

    attach_guidance_action = assign_guidance_action

    def run_guidance_notify(self, request, queryset):
        self._run_guidance(queryset, notify=True)
        self.message_user(
            request,
            _("Guidance is being run against selected messages. Users are notified."),
        )

    run_guidance_notify.short_description = _("Run guidance with user notifications")

    def run_guidance(self, request, queryset):
        self._run_guidance(queryset, notify=False)
        self.message_user(
            request, _("Guidance is being run against selected messages.")
        )

    run_guidance.short_description = _("Run guidance")

    def _run_guidance(self, queryset, notify=False):
        from froide.guide.tasks import run_guidance_on_queryset_task

        message_ids = queryset.values_list("id", flat=True)
        run_guidance_on_queryset_task.delay(message_ids, notify=notify)

    def get_deliverystatus_display(self, obj):
        return obj.deliverystatus.get_status_display()

    get_deliverystatus_display.short_description = _("delivery status")

    def check_delivery_status(self, request, queryset):
        from .tasks import check_delivery_status

        for message in queryset:
            check_delivery_status.delay(message.id, extended=True)
        self.message_user(
            request, _("Selected messages are being checked for delivery.")
        )

    check_delivery_status.short_description = _("Check delivery status")

    def resend_message(self, request, pk):
        if not request.method == "POST":
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        message = FoiMessage.objects.get(pk=pk, sent=False)
        message.request.is_blocked = False
        message.request.save()
        message.request.user.is_blocked = False
        message.request.user.save()
        message.force_resend()

        self.message_user(request, _("Message was send again."))
        return redirect("admin:foirequest_foimessage_change", message.id)

    def download_eml(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied

        message = FoiMessage.objects.get(pk=pk, kind="email")

        response = HttpResponse(
            message.as_mime_message().as_bytes(),
            content_type="application/octet-stream",
        )
        response[
            "Content-Disposition"
        ] = 'attachment; filename="message-{}.eml"'.format(message.id)
        return response

    def resend_messages(self, request, queryset):
        if not request.method == "POST":
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        count = 0
        total = len(queryset)
        queryset = queryset.filter(sent=False).select_related("request")
        for message in queryset:
            message.request.is_blocked = False
            message.request.save()
            message.request.user.is_blocked = False
            message.request.user.save()
            message.timestamp = timezone.now()
            message.force_resend()
            count += 1
        self.message_user(
            request,
            _("{num} of {total} selected messages were sent.").format(
                num=count, total=total
            ),
        )

    resend_message.short_description = _("Resend selected messages")


class MessageTagAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    actions = ["export_csv"]

    def export_csv(self, request, queryset):
        from froide.publicbody.models import PublicBody

        def get_stream(queryset):
            for tag in queryset:
                pbs = PublicBody.objects.filter(send_messages__tags=tag).annotate(
                    tag_count=models.Count(
                        "send_messages", filter=models.Q(send_messages__tags=tag)
                    )
                )
                for pb in pbs:
                    yield {
                        "tag": tag.name,
                        "publicbody_id": pb.id,
                        "publicbody_name": pb.name,
                        "tag_count": pb.tag_count,
                    }

        csv_stream = dict_to_csv_stream(get_stream(queryset))
        return export_csv_response(csv_stream, name="tag_stats.csv")

    export_csv.short_description = _("Export public body tag stats to CSV")


class FoiAttachmentAdmin(admin.ModelAdmin):
    raw_id_fields = ("belongs_to", "redacted", "converted", "document")
    ordering = ("-id",)
    date_hierarchy = "timestamp"
    list_display = (
        "name",
        "filetype",
        "size",
        "admin_link_message",
        "approved",
        "can_approve",
    )
    list_filter = (
        "can_approve",
        "approved",
        "is_redacted",
        "is_converted",
        make_nullfilter("redacted", _("Has redacted version")),
        make_nullfilter("converted", _("Has converted version")),
        "filetype",
        "pending",
        ("belongs_to__request", ForeignKeyFilter),
        ("belongs_to__request__user", ForeignKeyFilter),
    )
    search_fields = ["name"]
    formfield_overrides = {
        models.FileField: {"widget": AttachmentFileWidget},
    }
    actions = [
        "approve",
        "disapprove",
        "cannot_approve",
        "convert",
        "ocr_attachment",
        "make_document",
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("belongs_to")
        return qs

    def admin_link_message(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:foirequest_foimessage_change", args=(obj.belongs_to_id,)),
            _("See FoiMessage"),
        )

    def approve(self, request, queryset):
        rows_updated = queryset.update(approved=True)
        self.message_user(
            request, _("%d attachment(s) successfully approved." % rows_updated)
        )

    approve.short_description = _("Mark selected as approved")

    def disapprove(self, request, queryset):
        rows_updated = queryset.update(approved=False)
        self.message_user(
            request, _("%d attachment(s) successfully disapproved." % rows_updated)
        )

    disapprove.short_description = _("Mark selected as disapproved")

    def cannot_approve(self, request, queryset):
        rows_updated = queryset.update(can_approve=False, approved=False)
        self.message_user(
            request,
            _(
                "%d attachment(s) successfully marked as not approvable/approved."
                % rows_updated
            ),
        )

    cannot_approve.short_description = _("Mark selected as not approvable/approved")

    def convert(self, request, queryset):
        from .tasks import convert_attachment_task

        if not queryset:
            return
        count = 0
        for instance in queryset:
            if instance.can_convert_to_pdf():
                count += 1
                convert_attachment_task.delay(instance.pk)
        self.message_user(request, _("Conversion tasks started: %s") % count)

    convert.short_description = _("Convert to PDF")

    def make_document(self, request, queryset):
        count = 0
        for instance in queryset:
            doc = instance.create_document()
            if doc:
                count += 1
        self.message_user(request, _("%s document(s) created") % count)

    make_document.short_description = _("Make into document")

    def ocr_attachment(self, request, queryset):
        from .tasks import ocr_pdf_attachment

        for att in queryset:
            ocr_pdf_attachment(att)

    ocr_attachment.short_description = _("OCR PDF")


class FoiEventAdmin(admin.ModelAdmin):
    list_display = ("event_name", "user", "timestamp", "request")
    list_filter = (
        "event_name",
        "public",
        ("request", ForeignKeyFilter),
        ("user", ForeignKeyFilter),
        ("public_body", ForeignKeyFilter),
        ("message", ForeignKeyFilter),
    )
    search_fields = ["request__title", "public_body__name"]
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"
    raw_id_fields = ("request", "message", "user", "public_body")

    # Disable select_related from list_display
    list_select_related = (None,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related("request", "user")
        return qs


class PublicBodySuggestionAdmin(admin.ModelAdmin):
    list_display = (
        "request",
        "public_body",
        "user",
        "reason",
    )
    search_fields = ["request__title", "reason"]
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"
    raw_id_fields = ("request", "public_body", "user")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related("request", "public_body", "user")
        return qs


def execute_redeliver(admin, request, queryset, action_obj):
    for deferred in queryset:
        deferred.redeliver(action_obj)


class DeferredMessageAdmin(admin.ModelAdmin):
    model = DeferredMessage

    list_filter = ("delivered", make_nullfilter("request", _("Has request")), "spam")
    search_fields = (
        "recipient",
        "sender",
    )
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)
    list_display = (
        "recipient",
        "timestamp",
        "spam",
        "delivered",
        "sender",
        "request_last_message",
        "request_status",
        "request_page",
    )
    raw_id_fields = ("request",)
    actions = [
        "mark_as_spam",
        "deliver_no_spam",
        "redeliver",
        "redeliver_subject",
        "close_request",
    ]

    save_on_top = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("request")
        return qs

    def request_last_message(self, obj):
        if obj.request:
            return obj.request.last_message

    def request_status(self, obj):
        if obj.request:
            return obj.request.get_status_display()

    def request_page(self, obj):
        if obj.request:
            return format_html(
                '<a href="{}">{}</a>', obj.request.get_absolute_url(), obj.request.title
            )

    def close_request(self, request, queryset):
        for mes in queryset:
            mes.request.closed = True
            mes.request.save()
        return None

    close_request.short_description = _("Close associated requests")

    def redeliver_subject(self, request, queryset):
        for deferred in queryset:
            email = parse_email(BytesIO(deferred.encoded_mail()))
            match = SUBJECT_REQUEST_ID.search(email.subject)
            if match is not None:
                try:
                    req = FoiRequest.objects.get(pk=match.group(1))
                    deferred.redeliver(req)
                except FoiRequest.DoesNotExist:
                    continue

    redeliver_subject.short_description = _("Auto-Redeliver based on subject")

    def deliver_no_spam(self, request, queryset):
        for deferred in queryset:
            if deferred.request is not None:
                deferred.spam = False
                if deferred.delivered:
                    deferred.save()
                else:
                    deferred.redeliver(deferred.request)

    deliver_no_spam.short_description = _("Deliver and mark as no spam")

    def mark_as_spam(self, request, queryset):
        spam_senders = set()
        marked = 0
        deleted = 0
        for mes in queryset:
            if mes.sender in spam_senders:
                mes.delete()
                deleted += 1
                continue
            mes.spam = True
            mes.save()
            spam_senders.add(mes.sender)
            marked += 1
        self.message_user(
            request,
            _("Marked {marked} as spam, deleted {deleted} duplicates.").format(
                marked=marked, deleted=deleted
            ),
        )

    mark_as_spam.short_description = _(
        "Mark as spam (delete all except one per sender)"
    )

    redeliver = make_choose_object_action(
        FoiRequest, execute_redeliver, _("Redeliver to...")
    )


class FoiProjectAdminForm(forms.ModelForm):
    class Meta:
        model = FoiProject
        fields = "__all__"
        widgets = {
            "tags": TagAutocompleteWidget(
                autocomplete_url=reverse_lazy("api:request-tags-autocomplete")
            ),
        }


def execute_move_requests(admin, request, queryset, action_obj):
    assert not queryset.filter(id=action_obj.id).exists()

    for foi_project in queryset:
        action_obj.add_requests(FoiRequest.objects.filter(project=foi_project))


class FoiProjectAdmin(admin.ModelAdmin):
    form = FoiRequestAdminForm

    prepopulated_fields = {"slug": ("title",)}
    list_display = (
        "title",
        "created",
        "requests_admin_link",
        "user",
        "public",
        "status",
        "request_count",
        "site_link",
    )
    list_filter = ("public", "status", ("user", ForeignKeyFilter))
    search_fields = ["title", "description", "reference"]
    ordering = ("-last_update",)
    date_hierarchy = "created"
    raw_id_fields = (
        "user",
        "team",
        "publicbodies",
    )
    actions = ["move_requests", "publish"]

    def site_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>', obj.get_absolute_url(), _("Show on site")
        )

    def requests_admin_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:foirequest_foirequest_changelist")
            + ("?project__id__exact={}".format(obj.id)),
            _("Requests in admin"),
        )

    move_requests = make_choose_object_action(
        FoiProject, execute_move_requests, _("Move requests to...")
    )

    def publish(self, request, queryset):
        for foi_project in queryset:
            foi_project.make_public(publish_requests=True, user=request.user)

    publish.short_description = _("Publish project and all requests")


class RequestDraftAdmin(admin.ModelAdmin):
    list_display = (
        "save_date",
        "user",
        "subject",
    )
    list_filter = ("public", "full_text")
    search_fields = ["subject", "user__email"]
    ordering = ("-save_date",)
    date_hierarchy = "save_date"
    raw_id_fields = ("user", "publicbodies", "request", "project")


class DeliveryStatusAdmin(admin.ModelAdmin):
    raw_id_fields = ("message",)
    date_hierarchy = "last_update"
    list_display = ("message", "status", "last_update", "retry_count")
    list_filter = (
        "status",
        ("message", ForeignKeyFilter),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related("message", "message__request")
        return qs


admin.site.register(FoiRequest, FoiRequestAdmin)
admin.site.register(FoiMessage, FoiMessageAdmin)
admin.site.register(MessageTag, MessageTagAdmin)
admin.site.register(FoiAttachment, FoiAttachmentAdmin)
admin.site.register(FoiEvent, FoiEventAdmin)
admin.site.register(PublicBodySuggestion, PublicBodySuggestionAdmin)
admin.site.register(DeferredMessage, DeferredMessageAdmin)
admin.site.register(RequestDraft, RequestDraftAdmin)
admin.site.register(FoiProject, FoiProjectAdmin)
admin.site.register(DeliveryStatus, DeliveryStatusAdmin)
