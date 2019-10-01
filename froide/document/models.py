from django.db import models

from filingcabinet.models import (
    AbstractDocument,
    AbstractDocumentCollection,
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


class DocumentCollection(AbstractDocumentCollection):
    team = models.ForeignKey(
        'team.Team', null=True, blank=True,
        on_delete=models.SET_NULL
    )

    def is_public(self):
        return self.public
