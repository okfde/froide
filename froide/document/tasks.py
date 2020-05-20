from django.contrib.auth import get_user_model

from froide.celery import app as celery_app

from .models import DocumentCollection
from .services import UploadDocumentStorer

User = get_user_model()


@celery_app.task(name='froide.document.tasks.store_document_uploads')
def store_document_upload(upload_urls, user_id, form_data, collection_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    collection = None
    if collection_id:
        try:
            collection = DocumentCollection.objects.get(id=collection_id)
        except DocumentCollection.DoesNotExist:
            pass

    storer = UploadDocumentStorer(
        user,
        collection=collection,
        public=form_data['public'],
        tags=form_data['tags']
    )

    for upload_url in upload_urls:
        storer.create_from_upload_url(upload_url)
