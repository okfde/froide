from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from filingcabinet.admin import (
    DocumentBaseAdmin, PageAdmin, PageAnnotationAdmin,
    DocumentCollectionBaseAdmin,
    CollectionDocumentBaseAdmin
)
from filingcabinet.models import Page, PageAnnotation, CollectionDocument

from froide.helper.admin_utils import (
    ForeignKeyFilter, make_admin_assign_action
)
from froide.helper.forms import get_fk_form_class

from .models import Document, DocumentCollection


AddDocumentsToCollectionBaseMixin = make_admin_assign_action(
    'collection', _('Add documents to colletion')
)


class AddDocumentsToCollectionMixin(AddDocumentsToCollectionBaseMixin):
    def _get_assign_action_form_class(self, fieldname):
        return get_fk_form_class(
            CollectionDocument, 'collection', self.admin_site
        )

    def _execute_assign_action(self, obj, fieldname, assign_obj):
        CollectionDocument.objects.get_or_create(
            collection=assign_obj,
            document=obj
        )


class DocumentAdmin(AddDocumentsToCollectionMixin, DocumentBaseAdmin):
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
        DocumentBaseAdmin.actions + AddDocumentsToCollectionMixin.actions
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
