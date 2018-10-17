from django_elasticsearch_dsl.registries import registry

from django_elasticsearch_dsl.management.commands.search_index import Command as DESCommand

CHUNK_SIZE = 100


class Command(DESCommand):
    def _populate(self, models, options):
        for doc in registry.get_documents(models):
            qs = doc().get_queryset()
            chunk_size = getattr(doc._doc_type, 'queryset_pagination', CHUNK_SIZE)
            self.stdout.write(
                "Indexing {} '{}' objects "
                "with custom chunk_size {}".format(
                    qs.count(), doc._doc_type.model.__name__, chunk_size
                )
            )
            doc().update(qs, chunk_size=chunk_size)
