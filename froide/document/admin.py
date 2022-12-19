from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from filingcabinet.admin import (
    CollectionDirectoryAdmin,
    CollectionDocumentBaseAdmin,
    DocumentBaseAdmin,
    DocumentCollectionBaseAdmin,
    DocumentPortalAdmin,
    PageAdmin,
    PageAnnotationAdmin,
)
from filingcabinet.models import (
    CollectionDirectory,
    CollectionDocument,
    DocumentPortal,
    Page,
    PageAnnotation,
    TaggedDocument,
)

from froide.helper.admin_utils import (
    ForeignKeyFilter,
    TaggitListFilter,
    make_choose_object_action,
)
from froide.team.models import Team

from .models import Document, DocumentCollection
from .utils import update_document_index


def execute_add_document_to_collection(admin, request, queryset, action_obj):
    for obj in queryset:
        CollectionDocument.objects.get_or_create(collection=action_obj, document=obj)


def execute_set_team(admin, request, queryset, action_obj):
    queryset.update(team=action_obj)


class DocumentTagsFilter(TaggitListFilter):
    tag_class = TaggedDocument


class DocumentAdmin(DocumentBaseAdmin):
    raw_id_fields = DocumentBaseAdmin.raw_id_fields + (
        "original",
        "foirequest",
        "publicbody",
        "team",
    )
    list_filter = DocumentBaseAdmin.list_filter + (
        ("foirequest", ForeignKeyFilter),
        ("publicbody", ForeignKeyFilter),
        ("user", ForeignKeyFilter),
        ("team", ForeignKeyFilter),
        ("document_documentcollection", ForeignKeyFilter),
        DocumentTagsFilter,
    )
    actions = DocumentBaseAdmin.actions + ["add_document_to_collection", "set_team"]

    add_document_to_collection = make_choose_object_action(
        DocumentCollection,
        execute_add_document_to_collection,
        _("Add documents to collection..."),
    )

    set_team = make_choose_object_action(
        Team, execute_set_team, _("Set team for documents...")
    )

    def save_model(self, request, obj, form, change):
        res = super().save_model(request, obj, form, change)
        update_document_index(obj)
        return res

    def mark_listed(self, request, queryset):
        super().mark_listed(request, queryset)
        for doc in queryset:
            update_document_index(doc)

    mark_listed.short_description = _("Mark as listed")

    def mark_unlisted(self, request, queryset):
        super().mark_unlisted(request, queryset)
        for doc in queryset:
            update_document_index(doc)

    mark_unlisted.short_description = _("Mark as unlisted")


class CustomPageAdmin(PageAdmin):
    list_filter = PageAdmin.list_filter + (("document", ForeignKeyFilter),)


class CustomPageAnnotationAdmin(PageAnnotationAdmin):
    list_filter = [("page__document", ForeignKeyFilter), "page__number"]


class DocumentCollectionAdmin(DocumentCollectionBaseAdmin):
    raw_id_fields = DocumentCollectionBaseAdmin.raw_id_fields + ("team", "foirequests")
    actions = list(DocumentCollectionBaseAdmin.actions) + [
        "reindex_collection",
        "collect_documents_from_foirequests",
    ]

    def reindex_collection(self, request, queryset):
        for collection in queryset:
            for doc in collection.documents.all():
                update_document_index(doc)

    def collect_documents_from_foirequests(self, request, queryset):
        for collection in queryset:
            collection.update_from_foirequests()


class CollectionDocumentAdmin(CollectionDocumentBaseAdmin):
    list_filter = CollectionDocumentBaseAdmin.list_filter + (
        ("document", ForeignKeyFilter),
        ("collection", ForeignKeyFilter),
        ("directory", ForeignKeyFilter),
    )
    actions = list(CollectionDirectoryAdmin.actions) + ["move_to_directory"]

    def execute_move_to_directory(self, request, queryset, action_obj):
        queryset.update(directory=action_obj)

    move_to_directory = make_choose_object_action(
        CollectionDirectory,
        execute_move_to_directory,
        _("Move documents to directory..."),
    )


class CustomCollectionDirectoryAdmin(CollectionDirectoryAdmin):
    list_filter = CollectionDirectoryAdmin.list_filter + (
        ("collection", ForeignKeyFilter),
        ("user", ForeignKeyFilter),
    )


admin.site.register(Document, DocumentAdmin)
admin.site.register(Page, CustomPageAdmin)
admin.site.register(PageAnnotation, CustomPageAnnotationAdmin)
admin.site.register(DocumentCollection, DocumentCollectionAdmin)
admin.site.register(CollectionDocument, CollectionDocumentAdmin)
admin.site.register(DocumentPortal, DocumentPortalAdmin)
admin.site.register(CollectionDirectory, CustomCollectionDirectoryAdmin)
