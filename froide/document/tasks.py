from celery import shared_task

from .models import Document


@shared_task
def process_document(doc_pk):
    try:
        doc = Document.objects.get(pk=doc_pk)
    except Document.DoesNotExist:
        return None
    Document.objects.create_pages_from_pdf(doc)
