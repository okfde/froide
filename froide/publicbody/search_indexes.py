from __future__ import print_function

from django.conf import settings

from haystack import indexes

try:
    from celery_haystack.indexes import CelerySearchIndex as SearchIndex
except ImportError:
    SearchIndex = indexes.SearchIndex

from froide.helper.search import SuggestField

from .models import PublicBody

PUBLIC_BODY_BOOSTS = settings.FROIDE_CONFIG.get("public_body_boosts", {})


class PublicBodyIndex(SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', boost=1.5)
    name_auto = SuggestField(model_attr='all_names', boost=2.5)
    jurisdiction = indexes.FacetCharField(
        model_attr='jurisdiction__name',
        default=''
    )
    classification = indexes.FacetMultiValueField()
    categories = indexes.FacetMultiValueField()

    def get_model(self):
        return PublicBody

    def index_queryset(self, **kwargs):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.get_for_search_index()

    def prepare_classification(self, obj):
        if obj.classification is None:
            return []
        return [obj.classification.name] + [c.name for c in
                obj.classification.get_ancestors()]

    def prepare_categories(self, obj):
        cats = obj.categories.all()
        return [o.name for o in cats] + [
                c.name for o in cats for c in o.get_ancestors()]
