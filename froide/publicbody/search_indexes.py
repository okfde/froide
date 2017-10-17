from __future__ import print_function

from django.conf import settings

from haystack import indexes
from froide.helper.search import SuggestField

try:
    from celery_haystack.indexes import CelerySearchIndex as SearchIndex
except ImportError:
    SearchIndex = indexes.SearchIndex

from .models import PublicBody

PUBLIC_BODY_BOOSTS = settings.FROIDE_CONFIG.get("public_body_boosts", {})


class PublicBodyIndex(SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', boost=1.5)
    name_auto = SuggestField(model_attr='all_names')
    jurisdiction = indexes.FacetCharField(model_attr='jurisdiction__name', default='')
    tags = indexes.FacetMultiValueField()
    url = indexes.CharField(model_attr='get_absolute_url')

    def get_model(self):
        return PublicBody

    def index_queryset(self, **kwargs):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.get_for_search_index()

    def prepare_tags(self, obj):
        return [t.name for t in obj.tags.all()]

    def prepare(self, obj):
        data = super(PublicBodyIndex, self).prepare(obj)
        if obj.classification in PUBLIC_BODY_BOOSTS:
            data['boost'] = PUBLIC_BODY_BOOSTS[obj.classification]
            print("Boosting %s at %f" % (obj, data['boost']))
        return data
