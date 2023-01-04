from contextlib import contextmanager
from functools import partial

from django.db import models, transaction

from django_elasticsearch_dsl.registries import registry
from django_elasticsearch_dsl.signals import RealTimeSignalProcessor
from elasticsearch_dsl.connections import connections

from ..tasks import search_instance_delete, search_instance_save


@contextmanager
def realtime_search(testcase, test=True):
    signal_processor = CelerySignalProcessor(connections)
    signal_processor.setup()
    yield
    signal_processor.teardown()


class CelerySignalProcessor(RealTimeSignalProcessor):
    def setup(self):
        for doc in registry.get_documents():
            if getattr(doc, "special_signals", False):
                continue
            model = doc.django.model
            models.signals.post_save.connect(self.handle_save, sender=model)
            models.signals.post_delete.connect(self.handle_delete, sender=model)

            models.signals.m2m_changed.connect(self.handle_m2m_changed, sender=model)
            models.signals.pre_delete.connect(self.handle_pre_delete, sender=model)

    def teardown(self):
        # Listen to all model saves.
        for doc in registry.get_documents():
            if getattr(doc, "special_signals", False):
                continue
            model = doc.django.model
            models.signals.post_save.disconnect(self.handle_save, sender=model)
            models.signals.post_delete.disconnect(self.handle_delete, sender=model)
            models.signals.m2m_changed.disconnect(self.handle_m2m_changed, sender=model)
            models.signals.pre_delete.disconnect(self.handle_pre_delete, sender=model)

    def handle_save(self, sender, instance, **kwargs):
        """Handle save.

        Given an individual model instance, update the object in the index.
        Update the related objects either.
        """
        transaction.on_commit(
            partial(search_instance_save.delay, instance._meta.label_lower, instance.pk)
        )

    def handle_pre_delete(self, sender, instance, **kwargs):
        """Handle removing of instance object from related models instance.
        We need to do this before the real delete otherwise the relation
        doesn't exists anymore and we can't get the related models instance.
        """
        registry.delete_related(instance)

    def handle_delete(self, sender, instance, **kwargs):
        """Handle delete.

        Given an individual model instance, delete the object from index.
        """
        if instance.pk is None:
            return
        transaction.on_commit(
            partial(
                search_instance_delete.delay, instance._meta.label_lower, instance.pk
            )
        )
