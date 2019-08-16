from django.db.models import signals
from django.dispatch import receiver

from .models import Document


@receiver(signals.post_save, sender=Document,
        dispatch_uid="document_created")
def document_created(instance=None, created=False, **kwargs):
    if created and kwargs.get('raw', False):
        return
    if not created:
        return

    from filingcabinet.tasks import process_document_task
    process_document_task.delay(instance.pk)
