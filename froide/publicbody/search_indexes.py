from __future__ import print_function

from django.conf import settings

from haystack import indexes

try:
    from celery_haystack.indexes import CelerySearchIndex as SearchIndex
except ImportError:
    SearchIndex = indexes.SearchIndex

from .models import PublicBody

PUBLIC_BODY_BOOSTS = settings.FROIDE_CONFIG.get("public_body_boosts", {})


class PublicBodyIndex(SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', boost=1.5)
    jurisdiction = indexes.CharField(model_attr='jurisdiction__name', default='')
    name_auto = indexes.NgramField(model_attr='name')
    url = indexes.CharField(model_attr='get_absolute_url')

    def get_model(self):
        return PublicBody

    def index_queryset(self, **kwargs):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.get_for_search_index()

    def prepare(self, obj):
        data = super(PublicBodyIndex, self).prepare(obj)
        if obj.classification in PUBLIC_BODY_BOOSTS:
            data['boost'] = PUBLIC_BODY_BOOSTS[obj.classification]
            print("Boosting %s at %f" % (obj, data['boost']))
        return data
