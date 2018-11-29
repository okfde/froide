import itertools

from elasticsearch.exceptions import ConnectionError

from django_elasticsearch_dsl.registries import registry
from django_elasticsearch_dsl.management.commands.search_index import Command as DESCommand

# FIXME: DB chunk size only starting Django 2.0
DB_CHUNK_SIZE = 2000
CHUNK_SIZE = 100


def grouper(n, iterable):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


class Command(DESCommand):

    def _populate(self, models, options):
        for doc in registry.get_documents(models):
            qs = doc().get_queryset()
            count = qs.count()
            chunk_size = getattr(doc._doc_type, 'queryset_chunk_size', CHUNK_SIZE)
            self.stdout.write(
                "Indexing {} '{}' objects "
                "with custom chunk_size {}".format(
                    count, doc._doc_type.model.__name__, chunk_size
                )
            )
            obj_iterator = qs.iterator()
            for i, obj_group in enumerate(grouper(chunk_size, obj_iterator)):
                percentage = round(i / count * 100, 2)
                self.stdout.write('Indexing {}%'.format(
                    percentage
                ), ending='\r')
                tries = 1
                while True:
                    sub_group_size = chunk_size // tries
                    sub_groups = list(grouper(sub_group_size, obj_group))
                    try:
                        for sub_group in sub_groups:
                            doc().update(sub_group, chunk_size=sub_group_size)
                        break
                    except ConnectionError:
                        self.stdout.write('Failed chunk {} ({}%) at size {} with group {} ({} tries)'.format(
                            i, percentage, sub_group_size, [x.pk for x in sub_group], tries
                        ))
                        if tries < chunk_size:
                            tries += 1

            self.stdout.write('Done')
