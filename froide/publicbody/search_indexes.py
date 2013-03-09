from django.conf import settings

from haystack import indexes
from celery_haystack.indexes import CelerySearchIndex

from .models import PublicBody

PUBLIC_BODY_BOOSTS = settings.FROIDE_CONFIG.get("public_body_boosts", {})


class PublicBodyIndex(CelerySearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', boost=1.5)
    jurisdiction = indexes.CharField(model_attr='jurisdiction__name', default='')
    topic_auto = indexes.EdgeNgramField(model_attr='topic_name')
    topic_slug = indexes.CharField(model_attr='topic__slug')
    name_auto = indexes.EdgeNgramField(model_attr='name')
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
            print "Boosting %s at %f" % (obj, data['boost'])
        return data
