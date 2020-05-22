from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from filingcabinet.admin import (
    DocumentBaseAdmin, PageAdmin, PageAnnotationAdmin,
    DocumentCollectionBaseAdmin,
    CollectionDocumentBaseAdmin,
    CollectionDirectoryAdmin,
    DocumentPortalAdmin,
)
from filingcabinet.models import (
    Page, PageAnnotation, CollectionDocument,
    DocumentPortal, CollectionDirectory
)

from froide.helper.admin_utils import (
    ForeignKeyFilter, make_choose_object_action
)

from .models import Document, DocumentCollection


def execute_add_document_to_collection(admin, request, queryset, action_obj):
    for obj in queryset:
        CollectionDocument.objects.get_or_create(
            collection=action_obj,
            document=obj
        )


class DocumentAdmin(DocumentBaseAdmin):
    raw_id_fields = DocumentBaseAdmin.raw_id_fields + (
        'original', 'foirequest', 'publicbody', 'team'
    )
    list_filter = DocumentBaseAdmin.list_filter + (
        ('foirequest', ForeignKeyFilter),
        ('publicbody', ForeignKeyFilter),
        ('user', ForeignKeyFilter),
        ('team', ForeignKeyFilter),
    )
    actions = (
        DocumentBaseAdmin.actions
    )

    add_document_to_collection = make_choose_object_action(
        DocumentCollection, execute_add_document_to_collection,
        _('Add documents to collection')
    )


class CustomPageAdmin(PageAdmin):
    list_filter = PageAdmin.list_filter + (
        ('document', ForeignKeyFilter),
    )


class CustomPageAnnotationAdmin(PageAnnotationAdmin):
    list_filter = [
        ('page__document', ForeignKeyFilter),
        'page__number'
    ]


class DocumentCollectionAdmin(DocumentCollectionBaseAdmin):
    raw_id_fields = DocumentBaseAdmin.raw_id_fields + (
        'team',
    )


class CollectionDocumentAdmin(CollectionDocumentBaseAdmin):
    list_filter = CollectionDocumentBaseAdmin.list_filter + (
        ('document', ForeignKeyFilter),
        ('collection', ForeignKeyFilter),
    )


admin.site.register(Document, DocumentAdmin)
admin.site.register(Page, CustomPageAdmin)
admin.site.register(PageAnnotation, CustomPageAnnotationAdmin)
admin.site.register(DocumentCollection, DocumentCollectionAdmin)
admin.site.register(CollectionDocument, CollectionDocumentAdmin)
admin.site.register(DocumentPortal, DocumentPortalAdmin)
admin.site.register(CollectionDirectory, CollectionDirectoryAdmin)
