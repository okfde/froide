from haystack import indexes

from celery_haystack.indexes import CelerySearchIndex

from .models import FoiRequest


class FoiRequestIndex(CelerySearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title')
    description = indexes.CharField(model_attr='description')
    resolution = indexes.CharField(model_attr='resolution', default="")
    status = indexes.CharField(model_attr='status')
    readable_status = indexes.CharField(model_attr='readable_status')
    first_message = indexes.DateTimeField(model_attr='first_message')
    last_message = indexes.DateTimeField(model_attr='last_message')
    url = indexes.CharField(model_attr='get_absolute_url')
    public_body_name = indexes.CharField(model_attr='public_body__name', default="")

    def get_model(self):
        return FoiRequest

    def index_queryset(self, **kwargs):
        """Used when the entire index for model is updated."""
        return self.get_model().published.get_for_search_index()

    def should_update(self, instance, **kwargs):
        return (instance.visibility > 1 and
            instance.is_foi and instance.same_as is None)
