from haystack import indexes
from haystack import site

from foirequest.models import FoiRequest


class FoiRequestIndex(indexes.SearchIndex):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title')
    status = indexes.CharField(model_attr='status')
    first_message = indexes.DateTimeField(model_attr='first_message')
    last_message = indexes.DateTimeField(model_attr='last_message')
    

    def get_queryset(self):
        """Used when the entire index for model is updated."""
        return FoiRequest.objects.get_for_search_index()


site.register(FoiRequest, FoiRequestIndex)
