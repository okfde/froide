from django.conf import settings

from haystack import indexes
from haystack import site

from publicbody.models import PublicBody

PUBLIC_BODY_BOOSTS = getattr(settings, "FROIDE_PUBLIC_BODY_BOOSTS", {})

class PublicBodyIndex(indexes.SearchIndex):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', boost=1.5)
    geography = indexes.CharField(model_attr='geography')
    topic_auto = indexes.EdgeNgramField(model_attr='topic_name')
    topic_slug = indexes.CharField(model_attr='topic__slug')
    name_auto = indexes.EdgeNgramField(model_attr='name')
    url = indexes.CharField(model_attr='get_absolute_url')

    def get_queryset(self):
        """Used when the entire index for model is updated."""
        return PublicBody.objects.get_for_search_index()

    def prepare(self, obj):
        data = super(PublicBodyIndex, self).prepare(obj)
        if obj.classification in PUBLIC_BODY_BOOSTS:
            data['boost'] = PUBLIC_BODY_BOOSTS[obj.classification]
            print "Boosting %s at %f" % (obj, data['boost'])
        return data


site.register(PublicBody, PublicBodyIndex)
