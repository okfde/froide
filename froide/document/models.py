from django.db import models

from filingcabinet.models import (
    AbstractDocument,
    AbstractDocumentCollection,
    get_page_image_filename
)


class Document(AbstractDocument):
    original = models.ForeignKey(
        'foirequest.FoiAttachment', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='original_document'
    )

    foirequest = models.ForeignKey(
        'foirequest.FoiRequest', null=True, blank=True,
        on_delete=models.SET_NULL
    )
    publicbody = models.ForeignKey(
        'publicbody.PublicBody', null=True, blank=True,
        on_delete=models.SET_NULL
    )
    team = models.ForeignKey(
        'team.Team', null=True, blank=True,
        on_delete=models.SET_NULL
    )

    def is_public(self):
        return self.public

    def get_serializer_class(self, detail=False):
        from .api_views import DocumentSerializer, DocumentDetailSerializer

        if detail:
            return DocumentDetailSerializer
        return DocumentSerializer

    def get_crossdomain_auth(self, filename=None):
        from .auth import DocumentCrossDomainMediaAuth

        if filename is None:
            filename = self.get_document_filename()

        return DocumentCrossDomainMediaAuth({
            'object': self,
            'filename': filename
        })

    def get_authorized_file_url(self, filename=None):
        if self.public:
            return self.get_file_url(filename=filename)
        return self.get_crossdomain_auth(filename=filename).get_full_media_url(
            authorized=True
        )

    def get_page_template(self):
        return self.get_authorized_file_url(filename=get_page_image_filename())

    def get_cover_image(self):
        return self.get_authorized_file_url(filename=get_page_image_filename(
            page=1, size='small'
        ))


class DocumentCollection(AbstractDocumentCollection):
    team = models.ForeignKey(
        'team.Team', null=True, blank=True,
        on_delete=models.SET_NULL
    )

    def is_public(self):
        return self.public

    def get_serializer_class(self):
        from .api_views import DocumentCollectionSerializer

        return DocumentCollectionSerializer
