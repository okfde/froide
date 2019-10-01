from django.contrib import admin

from filingcabinet.admin import (
    DocumentBaseAdmin, PageAdmin, PageAnnotationAdmin,
    DocumentCollectionBaseAdmin
)
from filingcabinet.models import Page, PageAnnotation
from .models import Document, DocumentCollection


class DocumentAdmin(DocumentBaseAdmin):
    raw_id_fields = DocumentBaseAdmin.raw_id_fields + (
        'original', 'foirequest', 'publicbody', 'team'
    )


class DocumentCollectionAdmin(DocumentCollectionBaseAdmin):
    raw_id_fields = DocumentBaseAdmin.raw_id_fields + (
        'team',
    )


admin.site.register(Document, DocumentAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(PageAnnotation, PageAnnotationAdmin)
admin.site.register(DocumentCollection, DocumentCollectionAdmin)
