from django.contrib import admin

from filingcabinet.admin import (
    DocumentBaseAdmin, PageAdmin, PageAnnotationAdmin,
    DocumentCollectionBaseAdmin
)
from filingcabinet.models import Page, PageAnnotation

from froide.helper.admin_utils import ForeignKeyFilter

from .models import Document, DocumentCollection


class DocumentAdmin(DocumentBaseAdmin):
    raw_id_fields = DocumentBaseAdmin.raw_id_fields + (
        'original', 'foirequest', 'publicbody', 'team'
    )


class CustomPageAdmin(PageAdmin):
    list_filter = PageAdmin.list_filter + (
        ('document', ForeignKeyFilter),
    )


class CustomPageAnnotationAdmin(PageAnnotationAdmin):
    list_filter = (
        'page__number',
        ('page__document', ForeignKeyFilter),
    )


class DocumentCollectionAdmin(DocumentCollectionBaseAdmin):
    raw_id_fields = DocumentBaseAdmin.raw_id_fields + (
        'team',
    )


admin.site.register(Document, DocumentAdmin)
admin.site.register(Page, CustomPageAdmin)
admin.site.register(PageAnnotation, CustomPageAnnotationAdmin)
admin.site.register(DocumentCollection, DocumentCollectionAdmin)
