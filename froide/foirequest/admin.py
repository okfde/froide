from io import BytesIO
import re

from django.contrib import admin
from django.db import models
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.urls import reverse, reverse_lazy
from django.template.response import TemplateResponse
from django.contrib.admin import helpers
from django import forms
from django.conf.urls import url
from django.utils.html import format_html
from django.utils import timezone

from froide.helper.admin_utils import (
    make_nullfilter, make_greaterzerofilter, AdminTagAllMixIn,
    ForeignKeyFilter, TaggitListFilter, SearchFilter
)
from froide.helper.widgets import TagAutocompleteWidget
from froide.helper.forms import get_fk_form_class
from froide.helper.email_utils import EmailParser
from froide.guide.utils import GuidanceSelectionMixin
from froide.helper.csv_utils import dict_to_csv_stream, export_csv_response

from .models import (
    FoiRequest, FoiMessage, FoiProject,
    FoiAttachment, FoiEvent, PublicBodySuggestion, MessageTag,
    TaggedMessage, DeferredMessage, TaggedFoiRequest,
    RequestDraft, DeliveryStatus,
)
from .tasks import convert_attachment_task, ocr_pdf_attachment
from .widgets import AttachmentFileWidget
from .services import ActivatePendingRequestService
from .utils import update_foirequest_index


SUBJECT_REQUEST_ID = re.compile(r' \[#(\d+)\]')


class FoiMessageInline(admin.StackedInline):
    model = FoiMessage
    raw_id_fields = (
        'request', 'sender_user', 'sender_public_body', 'recipient_public_body',
        'original'
    )


class FoiRequestAdminForm(forms.ModelForm):
    class Meta:
        model = FoiRequest
        fields = '__all__'
        widgets = {
            'tags': TagAutocompleteWidget(
                autocomplete_url=reverse_lazy('api:request-tags-autocomplete')
            ),
        }


class FoiRequestTagsFilter(TaggitListFilter):
    tag_class = TaggedFoiRequest


class FoiRequestAdmin(admin.ModelAdmin, AdminTagAllMixIn):
    form = FoiRequestAdminForm

    prepopulated_fields = {"slug": ("title",)}
    inlines = [
        FoiMessageInline,
    ]
    list_display = ('title', 'first_message', 'secret_address', 'request_page',
                    'public_body', 'status', 'visibility')
    list_filter = ('jurisdiction', 'first_message', 'last_message', 'status',
        'resolution', 'is_foi', 'checked', 'public', 'visibility',
        'is_blocked', 'not_publishable',
        'campaign',
        make_nullfilter('same_as', _('Has same request')),
        ('user', ForeignKeyFilter), ('public_body', ForeignKeyFilter),
        ('project', ForeignKeyFilter), FoiRequestTagsFilter,
        make_greaterzerofilter('costs', _('Costs given'))
    )
    search_fields = ['title', 'description', 'secret_address', 'reference']
    ordering = ('-last_message',)
    date_hierarchy = 'first_message'

    tag_all_config = ('tags', reverse_lazy('api:request-tags-autocomplete'))

    actions = [
        'mark_checked', 'mark_not_foi',
        'mark_successfully_resolved', 'mark_refused',
        'tag_all', 'mark_same_as', 'update_index',
        'confirm_request', 'set_visible_to_user', 'unpublish',
        'add_to_project', 'unblock_request', 'close_requests'
    ]
    raw_id_fields = (
        'same_as', 'public_body', 'user', 'project',
        'jurisdiction', 'law'
    )
    save_on_top = True

    def request_page(self, obj):
        return format_html('<a href="{}">{}</a>',
            obj.get_absolute_url(), _('request page'))

    def mark_checked(self, request, queryset):
        rows_updated = queryset.update(checked=True)
        update_foirequest_index(queryset)
        self.message_user(request,
            _("%d request(s) successfully marked as checked." % rows_updated))
    mark_checked.short_description = _("Mark selected requests as checked")

    def mark_not_foi(self, request, queryset):
        rows_updated = queryset.update(
            is_foi=False,
            public=False,
            visibility=FoiRequest.VISIBLE_TO_REQUESTER
        )
        update_foirequest_index(queryset)
        self.message_user(request,
            _("%d request(s) successfully marked as not FoI." % rows_updated))
    mark_not_foi.short_description = _("Mark selected requests as not FoI")

    def mark_successfully_resolved(self, request, queryset):
        rows_updated = queryset.update(
            status='resolved', resolution='successful'
        )
        update_foirequest_index(queryset)
        self.message_user(request,
            _("%d request(s) have been marked as successfully resolved." %
                rows_updated))
    mark_successfully_resolved.short_description = _("Mark successfully resolved")

    def mark_refused(self, request, queryset):
        rows_updated = queryset.update(
            status='resolved', resolution='refused'
        )
        update_foirequest_index(queryset)
        self.message_user(request,
            _("%d request(s) have been marked as refused." %
                rows_updated))
    mark_refused.short_description = _("Mark as refused")

    def update_index(self, request, queryset):
        update_foirequest_index(queryset)
        self.message_user(request,
            _("%d request(s) will be updated in the search index." %
                queryset.count()))
    update_index.short_description = _("Update search index")

    def mark_same_as(self, request, queryset):
        """
        Mark selected requests as same as the one we are choosing now.

        """
        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        Form = get_fk_form_class(self.model, 'same_as', self.admin_site)
        # User has already chosen the other req
        if request.POST.get('obj'):
            f = Form(request.POST)
            if f.is_valid():
                req = f.cleaned_data['obj']
                queryset.update(same_as=req)
                count = FoiRequest.objects.filter(same_as=req).count()
                FoiRequest.objects.filter(id=req.id).update(
                    same_as_count=count
                )
                update_foirequest_index(queryset)
                self.message_user(request,
                    _("Successfully marked requests as identical."))
                # Return None to display the change list page again.
                return None
        else:
            f = Form()

        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'form': f,
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, 'foirequest/admin/mark_same_as.html',
            context)
    mark_same_as.short_description = _("Mark selected requests as identical to...")

    def confirm_request(self, request, queryset):
        foirequest = queryset[0]
        if foirequest.status != 'awaiting_user_confirmation':
            self.message_user(request, _("Request not in correct state!"))
            return None
        self.message_user(request, _("Message send successfully!"))
        req_service = ActivatePendingRequestService({
            'foirequest': foirequest
        })
        foirequest = req_service.process(request=None)
        return None
    confirm_request.short_description = _("Confirm request if unconfirmed")

    def set_visible_to_user(self, request, queryset):
        queryset.update(visibility=FoiRequest.VISIBLE_TO_REQUESTER)
        update_foirequest_index(queryset)
        self.message_user(request,
            _("Selected requests are now only visible to requester."))
    set_visible_to_user.short_description = _("Set only visible to requester")

    def unpublish(self, request, queryset):
        queryset.update(public=False)
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

        Form = get_fk_form_class(self.model, 'project', self.admin_site)
        # User has already chosen the other req
        if request.POST.get('obj'):
            f = Form(request.POST)
            if f.is_valid():
                project = f.cleaned_data['obj']
                project.add_requests(queryset)
                self.message_user(request,
                    _("Successfully added requests to project."))
                # Return None to display the change list page again.
                return None
        else:
            f = Form()

        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'form': f,
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(
            request,
            'foirequest/admin/add_to_project.html',
            context
        )
    add_to_project.short_description = _("Add selected requests to project...")


class FoiAttachmentInline(admin.TabularInline):
    model = FoiAttachment
    raw_id_fields = ('redacted', 'converted', 'document')
    formfield_overrides = {
        models.FileField: {'widget': AttachmentFileWidget},
    }


class DeliveryStatusInline(admin.TabularInline):
    model = DeliveryStatus
    extra = 0
    max_num = 1
    min_num = 0
    raw_id_fields = ('message',)
    readonly_fields = ('log', 'status', 'last_update')


class MessageTagsFilter(TaggitListFilter):
    tag_class = TaggedMessage


class FoiMessageAdmin(GuidanceSelectionMixin, admin.ModelAdmin):
    save_on_top = True
    list_display = (
        'subject', 'timestamp', 'message_page',
        'sender_email', 'recipient_email',
        'is_response', 'kind',
        'get_deliverystatus_display'
    )
    list_filter = (
        'kind', 'is_response', 'sent', 'status',
        'deliverystatus__status',
        make_nullfilter('deliverystatus', _('Has delivery status')),
        'sender_user__is_active',
        'sender_user__is_blocked',
        'sender_user__is_deleted',
        MessageTagsFilter,
        ('request__reference', SearchFilter),
        ('sender_public_body', ForeignKeyFilter),
        ('recipient_public_body', ForeignKeyFilter),
        ('request__user', ForeignKeyFilter),
        make_nullfilter('foiattachment_set', _('Has attachments')),
    )
    search_fields = ['subject', 'sender_email', 'recipient_email']
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    raw_id_fields = (
        'request', 'sender_user', 'sender_public_body',
        'recipient_public_body', 'original'
    )
    inlines = [
        DeliveryStatusInline,
        FoiAttachmentInline,
    ]
    actions = [
        'check_delivery_status', 'resend_messages',
        'run_guidance', 'run_guidance_notify',
        'attach_guidance_action'
    ]

    def get_urls(self):
        urls = super(FoiMessageAdmin, self).get_urls()
        my_urls = [
            url(r'^(?P<pk>\d+)/resend-message/$',
                self.admin_site.admin_view(self.resend_message),
                name='foirequest-foimessage-resend_message'),
        ]
        return my_urls + urls

    def get_queryset(self, request):
        qs = super(FoiMessageAdmin, self).get_queryset(request)
        qs = qs.select_related('deliverystatus')
        return qs

    def message_page(self, obj):
        return format_html('<a href="{}">{}</a>',
            obj.get_absolute_short_url(), _('on site'))

    def attach_guidance_action(self, request, queryset):
        ''' Magic from GuidanceSelectionMixin'''
        return self._assign_action_handler('', 'attach_guidance_action', request, queryset)
    attach_guidance_action.short_description = _('Add guidance action to messages')

    def run_guidance_notify(self, request, queryset):
        self._run_guidance(queryset, notify=True)
        self.message_user(request,
            _("Guidance is being run against selected messages. Users are notified."))
    run_guidance_notify.short_description = _("Run guidance with user notifications")

    def run_guidance(self, request, queryset):
        self._run_guidance(queryset, notify=False)
        self.message_user(request,
            _("Guidance is being run against selected messages."))
    run_guidance.short_description = _("Run guidance")

    def _run_guidance(self, queryset, notify=False):
        from froide.guide.tasks import run_guidance_on_queryset_task

        message_ids = queryset.values_list('id', flat=True)
        run_guidance_on_queryset_task.delay(message_ids, notify=notify)

    def get_deliverystatus_display(self, obj):
        return obj.deliverystatus.get_status_display()
    get_deliverystatus_display.short_description = _('delivery status')

    def check_delivery_status(self, request, queryset):
        from .tasks import check_delivery_status
        for message in queryset:
            check_delivery_status.delay(message.id, extended=True)
        self.message_user(request,
            _("Selected messages are being checked for delivery."))
    check_delivery_status.short_description = _("Check delivery status")

    def resend_message(self, request, pk):
        if not request.method == 'POST':
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        message = FoiMessage.objects.get(pk=pk, sent=False)
        message.request.is_blocked = False
        message.request.save()
        message.request.user.is_blocked = False
        message.request.user.save()
        message.force_resend()

        self.message_user(request, _('Message was send again.'))
        return redirect('admin:foirequest_foimessage_change', message.id)

    def resend_messages(self, request, queryset):
        if not request.method == 'POST':
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        count = 0
        total = len(queryset)
        queryset = queryset.filter(sent=False).select_related('request')
        for message in queryset:
            message.request.is_blocked = False
            message.request.save()
            message.request.user.is_blocked = False
            message.request.user.save()
            message.timestamp = timezone.now()
            message.force_resend()
            count += 1
        self.message_user(request,
            _("{num} of {total} selected messages were sent.").format(
                num=count, total=total
            ))
    resend_message.short_description = _('Resend selected messages')


class MessageTagAdmin(admin.ModelAdmin):
    actions = ['export_csv']

    def export_csv(self, request, queryset):
        from froide.publicbody.models import PublicBody

        def get_stream(queryset):
            for tag in queryset:
                pbs = PublicBody.objects.filter(
                    send_messages__tags=tag
                ).annotate(
                    tag_count=models.Count(
                        'send_messages',
                        filter=models.Q(
                            send_messages__tags=tag
                        )
                    )
                )
                for pb in pbs:
                    yield {
                        'tag': tag.name,
                        'publicbody_id': pb.id,
                        'publicbody_name': pb.name,
                        'tag_count': pb.tag_count
                    }
        csv_stream = dict_to_csv_stream(get_stream(queryset))
        return export_csv_response(csv_stream, name='tag_stats.csv')
    export_csv.short_description = _("Export public body tag stats to CSV")


class FoiAttachmentAdmin(admin.ModelAdmin):
    raw_id_fields = ('belongs_to', 'redacted', 'converted', 'document')
    ordering = ('-id',)
    date_hierarchy = 'timestamp'
    list_display = (
        'name', 'filetype', 'size', 'admin_link_message',
        'approved', 'can_approve',
    )
    list_filter = (
        'can_approve', 'approved', 'is_redacted', 'is_converted',
        make_nullfilter('redacted', _('Has redacted version')),
        make_nullfilter('converted', _('Has converted version')),
        'filetype',
        'pending',
        ('belongs_to__request', ForeignKeyFilter),
        ('belongs_to__request__user', ForeignKeyFilter),
    )
    search_fields = ['name']
    formfield_overrides = {
        models.FileField: {'widget': AttachmentFileWidget},
    }
    actions = ['approve', 'disapprove', 'cannot_approve',
               'convert', 'ocr_attachment', 'make_document']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('belongs_to')
        return qs

    def admin_link_message(self, obj):
        return format_html('<a href="{}">{}</a>',
            reverse('admin:foirequest_foimessage_change',
                args=(obj.belongs_to_id,)), _('See FoiMessage'))

    def approve(self, request, queryset):
        rows_updated = queryset.update(approved=True)
        self.message_user(request, _("%d attachment(s) successfully approved." % rows_updated))
    approve.short_description = _("Mark selected as approved")

    def disapprove(self, request, queryset):
        rows_updated = queryset.update(approved=False)
        self.message_user(request, _("%d attachment(s) successfully disapproved." % rows_updated))
    disapprove.short_description = _("Mark selected as disapproved")

    def cannot_approve(self, request, queryset):
        rows_updated = queryset.update(can_approve=False, approved=False)
        self.message_user(request, _("%d attachment(s) successfully marked as not approvable/approved." % rows_updated))
    cannot_approve.short_description = _("Mark selected as not approvable/approved")

    def convert(self, request, queryset):
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
        for att in queryset:
            ocr_pdf_attachment(att)
    ocr_attachment.short_description = _('OCR PDF')


class FoiEventAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'request', 'timestamp',)
    list_filter = ('event_name', 'public')
    search_fields = ['request__title', "public_body__name"]
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    raw_id_fields = ('request', 'user', 'public_body')


class PublicBodySuggestionAdmin(admin.ModelAdmin):
    list_display = ('request', 'public_body', 'user', 'reason',)
    search_fields = ['request', 'reason']
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    raw_id_fields = ('request', 'public_body', 'user')


class DeferredMessageAdmin(admin.ModelAdmin):
    model = DeferredMessage

    list_filter = ('delivered', make_nullfilter('request', _('Has request')),
                   'spam')
    search_fields = ('recipient', 'sender',)
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    list_display = (
        'recipient', 'timestamp', 'spam', 'delivered', 'sender',
        'request_last_message', 'request_status', 'request_page',)
    raw_id_fields = ('request',)
    actions = [
        'mark_as_spam', 'deliver_no_spam', 'redeliver', 'redeliver_subject',
        'close_request'
    ]

    save_on_top = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('request')
        return qs

    def request_last_message(self, obj):
        if obj.request:
            return obj.request.last_message

    def request_status(self, obj):
        if obj.request:
            return obj.request.get_status_display()

    def request_page(self, obj):
        if obj.request:
            return format_html('<a href="{}">{}</a>',
                obj.request.get_absolute_url(), obj.request.title)

    def close_request(self, request, queryset):
        for mes in queryset:
            mes.request.closed = True
            mes.request.save()
        return None
    close_request.short_description = _('Close associated requests')

    def redeliver_subject(self, request, queryset):
        parser = EmailParser()
        for deferred in queryset:
            email = parser.parse(BytesIO(deferred.encoded_mail()))
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
            ))
    mark_as_spam.short_description = _("Mark as spam (delete all except one per sender)")

    def redeliver(self, request, queryset, auto=False):
        """
        Redeliver undelivered mails

        """
        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        Form = get_fk_form_class(self.model, 'request', self.admin_site)
        # User has already chosen the other req
        if request.POST.get('obj'):
            f = Form(request.POST)
            if f.is_valid():
                req = f.cleaned_data['obj']
                for deferred in queryset:
                    deferred.redeliver(req)
                self.message_user(request,
                    _("Successfully triggered redelivery."))
                return None
        else:
            f = Form()

        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'form': f,
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, 'foirequest/admin_redeliver.html',
            context)
    redeliver.short_description = _("Redeliver to...")


class FoiProjectAdminForm(forms.ModelForm):
    class Meta:
        model = FoiProject
        fields = '__all__'
        widgets = {
            'tags': TagAutocompleteWidget(
                autocomplete_url=reverse_lazy('api:request-tags-autocomplete')
            ),
        }


class FoiProjectAdmin(admin.ModelAdmin):
    form = FoiRequestAdminForm

    prepopulated_fields = {"slug": ("title",)}
    list_display = ('title', 'created',
        'requests_admin_link',
        'user', 'public', 'status', 'request_count', 'site_link')
    list_filter = ('public', 'status',)
    search_fields = ['title', 'description', 'reference']
    ordering = ('-last_update',)
    date_hierarchy = 'created'
    raw_id_fields = ('user', 'team', 'publicbodies',)

    def site_link(self, obj):
        return format_html('<a href="{}">{}</a>',
            obj.get_absolute_url(),
            _('Show on site')
        )

    def requests_admin_link(self, obj):
        return format_html('<a href="{}">{}</a>',
            reverse('admin:foirequest_foirequest_changelist') + (
                '?project__id__exact={}'.format(obj.id)
            ),
            _('Requests in admin')
        )


class RequestDraftAdmin(admin.ModelAdmin):
    list_display = ('save_date', 'user', 'subject',)
    list_filter = ('public', 'full_text')
    search_fields = ['subject', 'user__email']
    ordering = ('-save_date',)
    date_hierarchy = 'save_date'
    raw_id_fields = ('user', 'publicbodies', 'request', 'project')


admin.site.register(FoiRequest, FoiRequestAdmin)
admin.site.register(FoiMessage, FoiMessageAdmin)
admin.site.register(MessageTag, MessageTagAdmin)
admin.site.register(FoiAttachment, FoiAttachmentAdmin)
admin.site.register(FoiEvent, FoiEventAdmin)
admin.site.register(PublicBodySuggestion, PublicBodySuggestionAdmin)
admin.site.register(DeferredMessage, DeferredMessageAdmin)
admin.site.register(RequestDraft, RequestDraftAdmin)
admin.site.register(FoiProject, FoiProjectAdmin)
