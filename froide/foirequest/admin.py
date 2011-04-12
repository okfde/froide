from django.contrib import admin
from froide.foirequest.models import FoiRequest, FoiMessage, FoiAttachment

class FoiMessageInline(admin.TabularInline):
    model = FoiMessage


class FoiRequestAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    inlines = [
        FoiMessageInline,
    ]

class FoiAttachmentInline(admin.TabularInline):
    model = FoiAttachment

class FoiMessageAdmin(admin.ModelAdmin):
    inlines = [
        FoiAttachmentInline,
    ]

class FoiAttachmentAdmin(admin.ModelAdmin):
    pass


admin.site.register(FoiRequest, FoiRequestAdmin)
admin.site.register(FoiMessage, FoiMessageAdmin)
admin.site.register(FoiAttachment, FoiAttachmentAdmin)
