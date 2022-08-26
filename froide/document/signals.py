from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver

from filingcabinet.models import CollectionDocument

from froide.foirequest.models import FoiAttachment

from .models import Document
from .utils import update_document_index


@receiver(signals.post_save, sender=Document, dispatch_uid="document_created")
def document_created(instance=None, created=False, **kwargs):
    if created and kwargs.get("raw", False):
        return
    if not created:
        update_document_index(instance)
        return


@receiver(
    FoiAttachment.attachment_approved, dispatch_uid="was_redacted_reprocess_document"
)
def reprocess_document_after_redaction(sender: FoiAttachment, **kwargs):
    if sender.document and kwargs.get("redacted"):
        # Recreate pages after redaction
        sender.document.process_document(reprocess=True)
        return
    unredacteds = sender.unredacted_set.all()
    if not unredacteds:
        return
    assert len(unredacteds) == 1
    original = unredacteds[0]
    doc_id = original.document_id
    if doc_id:
        # Original has a document
        # Move references to redacted version (=sender)
        with transaction.atomic():
            Document.objects.filter(id=doc_id).update(original_id=sender.id)
            original.document = None
            original.save(update_fields=["document"])
            FoiAttachment.objects.filter(id=sender.id).update(document_id=doc_id)
        # Then reprocess document
        document = Document.objects.get(id=doc_id)
        document.process_document(reprocess=True)


@receiver(
    signals.post_delete,
    sender=CollectionDocument,
    dispatch_uid="reindex_document_removed_from_collection",
)
def reindex_document_removed_from_collection(instance: CollectionDocument, **kwargs):
    update_document_index(instance.document)
