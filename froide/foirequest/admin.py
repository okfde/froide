from django.contrib import admin
from django.utils.translation import ugettext as _
from django.core.exceptions import PermissionDenied
from django.db import router
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe
from django.contrib.admin import helpers

from taggit.utils import parse_tags

from froide.helper.admin_utils import NullFilterSpec

from .models import (FoiRequest, FoiMessage,
        FoiAttachment, FoiEvent, PublicBodySuggestion,
        DeferredMessage)
from .tasks import count_same_foirequests, convert_attachment


class FoiMessageInline(admin.StackedInline):
    model = FoiMessage
    raw_id_fields = ('request', 'sender_user', 'sender_public_body', 'recipient_public_body')


class FoiRequestAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    inlines = [
        FoiMessageInline,
    ]
    list_display = ('title', 'first_message', 'user', 'checked',
        'public_body', 'status',)
    list_filter = ('checked', 'first_message', 'last_message', 'status',
        'resolution', 'is_foi', 'public')
    search_fields = ['title', "description", 'secret_address']
    ordering = ('-last_message',)
    date_hierarchy = 'first_message'
    actions = ['mark_checked', 'mark_not_foi', 'tag_all',
               'mark_same_as', 'remove_from_index']
    raw_id_fields = ('same_as', 'public_body', 'user',)
    save_on_top = True

    def mark_checked(self, request, queryset):
        rows_updated = queryset.update(checked=True)
        self.message_user(request, _("%d request(s) successfully marked as checked." % rows_updated))
    mark_checked.short_description = _("Mark selected requests as checked")

    def mark_not_foi(self, request, queryset):
        rows_updated = queryset.update(is_foi=False)
        self.message_user(request, _("%d request(s) successfully marked as not FoI." % rows_updated))
    mark_not_foi.short_description = _("Mark selected requests as not FoI")

    def mark_same_as(self, request, queryset):
        """
        Mark selected requests as same as the one we are choosing now.

        """
        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        # User has already chosen the other req
        if request.POST.get('req_id'):
            try:
                req = self.model.objects.get(id=int(request.POST.get('req_id')))
            except (ValueError, self.model.DoesNotExist,):
                raise PermissionDenied
            queryset.update(same_as=req)
            count_same_foirequests.delay(req.id)
            self.message_user(request, _("Successfully marked requests as identical."))
            # Return None to display the change list page again.
            return None

        db = router.db_for_write(self.model)
        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'req_widget': mark_safe(admin.widgets.ForeignKeyRawIdWidget(
                    self.model._meta.get_field(
                        'same_as').rel, self.admin_site, using=db).render(
                            'req_id', None,
                            {'id': 'id_req_id'})
                            .replace('../../..', '../..')),
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, 'foirequest/admin_mark_same_as.html',
            context, current_app=self.admin_site.name)

    mark_same_as.short_description = _("Mark selected requests as identical to...")

    def tag_all(self, request, queryset):
        """
        Tag all selected requests with given tags

        """
        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        # User has already chosen the other req
        if request.POST.get('tags'):
            tags = parse_tags(request.POST.get('tags'))
            for obj in queryset:
                obj.tags.add(*tags)
                obj.save()
            self.message_user(request, _("Successfully added tags to requests"))
            # Return None to display the change list page again.
            return None

        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, 'foirequest/admin_tag_all.html',
            context, current_app=self.admin_site.name)

    tag_all.short_description = _("Tag all requests with...")

    def remove_from_index(self, request, queryset):
        from haystack import connections as haystack_connections

        for obj in queryset:
            for using in haystack_connections.connections_info.keys():
                backend = haystack_connections[using].get_backend()
                backend.remove(obj)

        self.message_user(request, _("Removed from search index"))
    remove_from_index.short_description = _("Remove from search index")


class FoiAttachmentInline(admin.TabularInline):
    model = FoiAttachment
    raw_id_fields = ('redacted', 'converted')


class FoiMessageAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('subject', 'timestamp', 'sender_email', 'recipient_email',)
    list_filter = ('is_postal', 'is_response', 'sent', 'status',)
    search_fields = ['subject', 'sender_email', 'recipient_email']
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    exclude = ('original',)
    raw_id_fields = ('request', 'sender_user', 'sender_public_body', 'recipient_public_body')
    inlines = [
        FoiAttachmentInline,
    ]


class FoiAttachmentAdmin(admin.ModelAdmin):
    raw_id_fields = ('belongs_to', 'redacted', 'converted')
    ordering = ('-id',)
    list_display = ('name', 'filetype', 'admin_link_message', 'approved', 'can_approve',)
    list_filter = ('can_approve', 'approved',)
    search_fields = ['name']
    actions = ['approve', 'cannot_approve', 'convert']

    def approve(self, request, queryset):
        rows_updated = queryset.update(approved=True)
        self.message_user(request, _("%d attachment(s) successfully approved." % rows_updated))
    approve.short_description = _("Mark selected as approved")

    def cannot_approve(self, request, queryset):
        rows_updated = queryset.update(can_approve=False)
        self.message_user(request, _("%d attachment(s) successfully marked as not approvable." % rows_updated))
    cannot_approve.short_description = _("Mark selected as NOT approvable")

    def convert(self, request, queryset):
        if not queryset:
            return
        instance = queryset[0]
        if (instance.filetype in FoiAttachment.CONVERTABLE_FILETYPES or
                instance.name.endswith(FoiAttachment.CONVERTABLE_FILETYPES)):
            convert_attachment(instance)
            self.message_user(request, _("Converted to PDF."))
    convert.short_description = _("Convert to PDF")


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


class RequestNullFilter(NullFilterSpec):
    title = _(u'Has request')
    parameter_name = u'request'


class DeferredMessageAdmin(admin.ModelAdmin):
    model = DeferredMessage

    list_filter = (RequestNullFilter,)
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    list_display = ('recipient', 'timestamp', 'request')
    raw_id_fields = ('request',)
    actions = ['redeliver']

    def redeliver(self, request, queryset):
        """
        Redeliver undelivered mails

        """
        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        # User has already chosen the other req
        if request.POST.get('req_id'):
            req_id = int(request.POST.get('req_id'))
            try:
                req = FoiRequest.objects.get(id=req_id)
            except (ValueError, FoiRequest.DoesNotExist,):
                raise PermissionDenied

            for deferred in queryset:
                deferred.redeliver(req)

            self.message_user(request, _("Successfully triggered redelivery."))

            return None

        db = router.db_for_write(self.model)
        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'req_widget': mark_safe(admin.widgets.ForeignKeyRawIdWidget(
                    self.model._meta.get_field(
                        'request').rel, self.admin_site, using=db).render(
                            'req_id', None,
                            {'id': 'id_req_id'})
                            .replace('../../..', '../..')),
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, 'foirequest/admin_redeliver.html',
            context, current_app=self.admin_site.name)
    redeliver.short_description = _("Redeliver to...")

admin.site.register(FoiRequest, FoiRequestAdmin)
admin.site.register(FoiMessage, FoiMessageAdmin)
admin.site.register(FoiAttachment, FoiAttachmentAdmin)
admin.site.register(FoiEvent, FoiEventAdmin)
admin.site.register(PublicBodySuggestion, PublicBodySuggestionAdmin)
admin.site.register(DeferredMessage, DeferredMessageAdmin)
