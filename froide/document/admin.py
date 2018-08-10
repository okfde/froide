from django.contrib import admin

from filingcabinet.admin import DocumentBaseAdmin, PageAdmin, PageAnnotationAdmin
from filingcabinet.models import Page, PageAnnotation
from .models import Document


class DocumentAdmin(DocumentBaseAdmin):
    raw_id_fields = DocumentBaseAdmin.raw_id_fields + (
        'original', 'foirequest', 'publicbody'
    )


admin.site.register(Document, DocumentAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(PageAnnotation, PageAnnotationAdmin)
