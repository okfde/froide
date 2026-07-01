from django.contrib.auth import get_user_model

from froide.celery import app as celery_app

from .models import DocumentCollection

User = get_user_model()


@celery_app.task(name="froide.document.tasks.store_document_uploads")
def store_document_upload(upload_urls, user_id, form_data, collection_id):
    from .services import UploadDocumentStorer

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
        user, collection=collection, public=form_data["public"], tags=form_data["tags"]
    )

    for upload_url in upload_urls:
        storer.create_from_upload_url(upload_url)


@celery_app.task(name="froide.document.tasks.index_document")
def index_document(document_id):
    from .models import Document
    from .utils import update_document_index_internal

    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return
    update_document_index_internal(document)


@celery_app.task(name="froide.document.tasks.index_documentcollection")
def index_documentcollection(collection_id):
    from .models import DocumentCollection
    from .utils import update_document_index_internal

    try:
        collection = DocumentCollection.objects.get(id=collection_id)
    except DocumentCollection.DoesNotExist:
        return

    for document in collection.documents.all():
        update_document_index_internal(document)
