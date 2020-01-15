from django.utils.safestring import mark_safe

from elasticsearch_dsl import A
from elasticsearch_dsl.query import Q


def _make_values_lists(kwargs):
    return {
        k: v if isinstance(v, (list, tuple)) else [v]
        for k, v in kwargs.items()
    }


class EmtpyResponse(list):
    class hits:
        total = 0


class SearchQuerySetWrapper(object):
    """
    Decorates a SearchQuerySet object using a generator for efficient iteration
    """
    def __init__(self, sqs, model):
        self.sqs = sqs
        self.sqs.model = model
        self.model = model
        self.filters = []
        self.query = None
        self.aggs = []
        self.broken_query = False

    def count(self):
        return self.response.hits.total

    def to_queryset(self):
        if self.broken_query:
            return self.model.objects.none()
        return self.sqs.to_queryset()

    def wrap_queryset(self, qs):
        return ESQuerySetWrapper(qs, self.response)

    def update_query(self):
        if self.filters:
            self.sqs.post_filter = Q('bool', must=self.filters)

    def all(self):
        return self

    @property
    def response(self):
        return self.get_response()

    def get_response(self):
        if not hasattr(self.sqs, '_response'):
            self.sqs = self.sqs.source(excludes=['*'])
        else:
            return self.sqs._response
        try:
            return self.sqs.execute()
        except Exception:
            self.broken_query = True
            return EmtpyResponse()

    def add_aggregation(self, aggs):
        for field in aggs:
            a = A('terms', field=field)
            self.sqs.aggs.bucket(field, a)
        return self

    def get_facets(self, resolvers=None):
        if resolvers is None:
            resolvers = {}
        return {
            k: resolvers[k](k, self.response['aggregations'][k])
            for k in self.response['aggregations']
            if k in resolvers
        }

    def get_aggregations(self):
        if self.broken_query:
            return {
                'fields': {}
            }
        return {'fields': {
            k: [
                [i['key'], i['doc_count']]
                for i in self.response['aggregations'][k]['buckets']
            ]
            for k in self.response['aggregations']
        }}

    def filter(self, *args, **kwargs):
        if kwargs:
            value = Q('terms', **_make_values_lists(kwargs))
        else:
            value = args[0]
        self.filters.append(value)
        self.update_query()
        return self

    def set_query(self, q):
        self.query = q
        self.sqs = self.sqs.query(self.query)
        return self

    def add_sort(self, *sorts):
        self.sqs = self.sqs.sort(*sorts)
        return self

    def __getitem__(self, key):
        self.sqs = self.sqs[key]
        return self

    def __iter__(self):
        return iter(self.sqs)


class ESQuerySetWrapper(object):
    def __init__(self, qs, es_response):
        self.__class__ = type(
            qs.__class__.__name__,
            (self.__class__, qs.__class__),
            {}
        )
        self.__dict__ = qs.__dict__
        self._qs = qs
        self._es_response = es_response
        self._es_map = {
            int(hit.meta.id): hit for hit in es_response
        }

    def __iter__(self):
        for obj in self._qs:
            hit = self._es_map[obj.pk]
            # mark_safe should work because highlight_options
            # has been set with encoder="html"
            obj.query_highlight = mark_safe(' '.join(self._get_highlight(hit)))
            yield obj

    def _get_highlight(self, hit):
        if hasattr(hit.meta, 'highlight'):
            for key in hit.meta.highlight:
                yield from hit.meta.highlight[key]
