from froide.celery import app as celery_app
from froide.upload.models import Upload

from filingcabinet.tasks import process_document_task

from .models import Document


@celery_app.task(name='froide.document.tasks.move_upload_to_document')
def move_upload_to_document(doc_id, upload_id):
    try:
        doc = Document.objects.get(pk=doc_id)
    except Document.DoesNotExist:
        return

    try:
        upload = Upload.objects.get(pk=upload_id)
    except Upload.DoesNotExist:
        return

    file = upload.get_file()
    if file:
        doc.pdf_file.save(upload.filename, file, save=True)
        process_document_task.delay(doc.pk)
    upload.finish()
    upload.delete()
