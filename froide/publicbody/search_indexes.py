from haystack import indexes
from haystack import site

from publicbody.models import PublicBody


class PublicBodyIndex(indexes.SearchIndex):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name')
    geography = indexes.CharField(model_attr='geography')
    topic_auto = indexes.EdgeNgramField(model_attr='topic')
    name_auto = indexes.EdgeNgramField(model_attr='name')
    url = indexes.CharField(model_attr='get_absolute_url')

    def get_queryset(self):
        """Used when the entire index for model is updated."""
        return PublicBody.objects.get_for_search_index()


site.register(PublicBody, PublicBodyIndex)
