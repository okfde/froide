from froide.helper.tasks import search_instance_save


def update_document_index(document):
    for pk in document.page_set.all().values_list('id', flat=True):
        search_instance_save.delay('filingcabinet.page', pk)
