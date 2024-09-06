from django.core.management.base import BaseCommand

from django_elasticsearch_dsl.management.commands.search_index import (
    Command as DESCommand,
)
from django_elasticsearch_dsl.registries import registry
from elasticsearch_dsl import Q, connections


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.es_conn = connections.get_connection()

    def add_arguments(self, parser):
        parser.add_argument(
            "--models",
            metavar="app[.model]",
            type=str,
            nargs="*",
            help="Specify the model or app to be updated in elasticsearch",
        )

    _get_models = DESCommand._get_models

    def handle(self, *args, **options):
        models = self._get_models(options["models"])

        for doc in registry.get_documents(models):
            es_ids = {int(hit.meta.id) for hit in doc().search().source(False).scan()}
            db_ids = set(doc().get_queryset().values_list("pk", flat=True))
            deleted_ids = es_ids - db_ids
            print(
                f"Deleting {len(deleted_ids)} '{doc.django.model.__name__}' documents from ES"
            )
            res = doc().search().query(Q("ids", values=list(deleted_ids))).delete()
            print(
                f"Successfully deleted {res.deleted} '{doc.django.model.__name__}' documents in {res.took}ms"
            )
