from django.contrib import admin
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .models import Document, Page, PageAnnotation
from .tasks import process_document


class PageInline(admin.StackedInline):
    model = Page
    raw_id_fields = ('document',)


class DocumentAdmin(admin.ModelAdmin):
    inlines = [PageInline]
    list_display = ('title', 'created_at', 'num_pages', 'public')
    raw_id_fields = ('user',)
    readonly_fields = ('uid',)
    actions = ('reprocess_document',)

    def save_model(self, request, doc, form, change):
        doc.updated_at = timezone.now()
        super(DocumentAdmin, self).save_model(
            request, doc, form, change)
        if not change:
            process_document.delay(doc.pk)

    def reprocess_document(self, request, queryset):
        for instance in queryset:
            Document.objects.create_pages_from_pdf(instance)
    reprocess_document.short_description = _("Reprocess document")


class PageAdmin(admin.ModelAdmin):
    raw_id_fields = ('document',)


class PageAnnotationAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'page',)


admin.site.register(Document, DocumentAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(PageAnnotation, PageAnnotationAdmin)
