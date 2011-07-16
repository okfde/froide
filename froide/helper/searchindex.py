from django.db.models import signals

from haystack.indexes import SearchIndex

from helper.tasks import delayed_update, delayed_remove


class QueuedRealTimeSearchIndex(SearchIndex):
    """
    A variant of the ``SearchIndex`` that constantly keeps the index fresh,
    by queueing index jobs with celery
    """
    def _setup_save(self, model):
        signals.post_save.connect(self.delayed_update, sender=model)
    
    def _setup_delete(self, model):
        signals.post_delete.connect(self.delayed_remove, sender=model)
    
    def _teardown_save(self, model):
        signals.post_save.disconnect(self.delayed_update, sender=model)
    
    def _teardown_delete(self, model):
        signals.post_delete.disconnect(self.delayed_remove, sender=model)

    def delayed_update(self, instance, **kwargs):
        delayed_update.delay(instance.pk, kwargs['sender'])

    def delayed_remove(self, instance, **kwargs):
        delayed_remove.delay(instance.pk, kwargs['sender'])


