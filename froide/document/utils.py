from froide.helper.tasks import search_instance_save

from .models import Document


def update_document_index(document: Document) -> None:
    for pk in document.pages.all().values_list("id", flat=True):
        search_instance_save.delay("filingcabinet.page", pk)
