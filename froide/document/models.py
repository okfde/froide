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


class DocumentCollection(AbstractDocumentCollection):
    pass
