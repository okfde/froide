from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver

from froide.foirequest.models import FoiAttachment

from .models import Document, DocumentCollection
from .utils import update_document_index


@receiver(signals.post_save, sender=Document,
        dispatch_uid="document_created")
def document_created(instance=None, created=False, **kwargs):
    if created and kwargs.get('raw', False):
        return
    if not created:
        update_document_index(instance)
        return

    from filingcabinet.tasks import process_document_task
    process_document_task.delay(instance.pk)


@receiver(signals.post_save, sender=DocumentCollection,
        dispatch_uid="documentcollection_updated")
def collection_updated(instance=None, created=False, **kwargs):
    if created or kwargs.get('raw', False):
        return

    for doc in instance.documents.all():
        update_document_index(doc)


@receiver(signals.post_save, sender=FoiAttachment,
        dispatch_uid='reprocess_attachment_redaction')
def reprocess_attachment_redaction(instance, created=False, **kwargs):
    if created and kwargs.get('raw', False):
        return
    if not instance.document_id:
        return
    if not instance.redacted_id:
        return
    # If attachment has document, but also redacted version
    # move document reference to redacted version
    with transaction.atomic():
        doc_id = instance.document_id
        Document.objects.filter(id=doc_id).update(
            original_id=instance.redacted_id
        )
        instance.document = None
        instance.save()
        FoiAttachment.objects.filter(
            id=instance.redacted_id
        ).update(document_id=doc_id)

    d = Document.objects.get(id=doc_id)
    d.process_document()


@receiver(FoiAttachment.attachment_redacted,
          dispatch_uid='was_redacted_reprocess_document')
def reprocess_document_after_redaction(sender, **kwargs):
    if sender.document:
        sender.document.process_document()
