from filingcabinet.services import DocumentStorer

from froide.upload.models import Upload


class UploadDocumentStorer(DocumentStorer):
    def create_from_upload_url(self, upload_url):
        try:
            upload = Upload.objects.get_by_url(
                upload_url, user=self.user
            )
        except Upload.DoesNotExist:
            return None
        return self.create_from_upload(upload)

    def create_from_upload(self, upload):
        upload.ensure_saving()
        upload.save()

        if upload.filename.endswith('.pdf'):
            self.create_document_from_upload(upload)
        elif upload.filename.endswith('.zip') and self.collection:
            self.unpack_upload_zip(upload)

        upload.finish()
        upload.delete()

    def create_document_from_upload(self, upload):
        file_obj = upload.get_file()
        return self.create_from_file(file_obj, upload.filename)
