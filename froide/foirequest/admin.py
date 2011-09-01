from django.contrib import admin
from django.utils.translation import ugettext as _
from froide.foirequest.models import (FoiRequest, FoiMessage,
        FoiAttachment, FoiEvent, PublicBodySuggestion)


class FoiMessageInline(admin.TabularInline):
    model = FoiMessage


class FoiRequestAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    inlines = [
        FoiMessageInline,
    ]
    list_display = ('title', 'first_message', 'user', 'checked', 'public_body', 'status',)
    list_filter = ('checked', 'first_message', 'last_message', 'status', 'is_foi', 'public')
    search_fields = ['title', "description", 'secret_address']
    ordering = ('-last_message',)
    date_hierarchy = 'first_message'
    actions = ['mark_checked', 'mark_not_foi']

    def mark_checked(self, request, queryset):
        rows_updated = queryset.update(checked=True)
        self.message_user(request, _("%d request(s) successfully marked as checked." % rows_updated))
    mark_checked.short_description = _("Mark selected requests as checked")

    def mark_not_foi(self, request, queryset):
        rows_updated = queryset.update(is_foi=False)
        self.message_user(request, _("%d request(s) successfully marked as not FoI." % rows_updated))
    mark_not_foi.short_description = _("Mark selected requests as not FoI")


class FoiAttachmentInline(admin.TabularInline):
    model = FoiAttachment


class FoiMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender_user', 'sender_email', 'recipient_email',)
    list_filter = ('is_postal', 'is_response', 'sent', 'status',)
    search_fields = ['subject', 'sender_email', 'recipient_email']
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    inlines = [
        FoiAttachmentInline,
    ]


class FoiAttachmentAdmin(admin.ModelAdmin):
    pass


class FoiEventAdmin(admin.ModelAdmin):
    pass


class PublicBodySuggestionAdmin(admin.ModelAdmin):
    pass


admin.site.register(FoiRequest, FoiRequestAdmin)
admin.site.register(FoiMessage, FoiMessageAdmin)
admin.site.register(FoiAttachment, FoiAttachmentAdmin)
admin.site.register(FoiEvent, FoiEventAdmin)
admin.site.register(PublicBodySuggestion, PublicBodySuggestionAdmin)
