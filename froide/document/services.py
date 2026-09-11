from filingcabinet.services import DocumentStorer

from froide.document.models import Document
from froide.upload.models import Upload


class UploadDocumentStorer(DocumentStorer):
    def create_from_upload_url(self, upload_url) -> list[Document] | None:
        try:
            upload = Upload.objects.get_by_url(upload_url, user=self.user)
        except Upload.DoesNotExist:
            return None
        return self.create_from_upload(upload)

    def create_from_upload(self, upload) -> list[Document]:
        upload.ensure_saving()
        upload.save()

        docs = []

        if upload.filename.lower().endswith(".pdf"):
            docs = [self.create_document_from_upload(upload)]
        elif upload.filename.lower().endswith(".zip") and self.collection:
            docs = self.unpack_upload_zip(upload)

        upload.finish()
        upload.delete()

        return docs

    def create_document_from_upload(self, upload) -> Document:
        file_obj = upload.get_file()
        return self.create_from_file(file_obj, upload.filename)
