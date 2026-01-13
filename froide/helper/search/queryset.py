import difflib
import html
import logging
import re

from django.utils.safestring import mark_safe

from elasticsearch_dsl import A
from elasticsearch_dsl.query import Q

logger = logging.getLogger(__name__)


def _make_values_lists(kwargs):
    return {k: v if isinstance(v, (list, tuple)) else [v] for k, v in kwargs.items()}


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
        self.post_filters = []
        self.aggregations = []
        self.applied_post_filters = {}
        self.query = None
        self.aggs = []
        self.broken_query = False

    def count(self):
        total = self.response.hits.total
        if isinstance(total, int):
            return total
        return total.value

    def has_more(self):
        total = self.response.hits.total
        if isinstance(total, int):
            return False
        return total.relation == "gte"

    def to_queryset(self):
        if self.broken_query:
            return self.model.objects.none()
        return self.sqs.to_queryset()

    def wrap_queryset(self, qs):
        return ESQuerySetWrapper(qs, self.response)

    def update_query(self):
        if self.post_filters:
            self.sqs = self.sqs.post_filter(Q("bool", must=self.post_filters))
        if self.filters:
            self.sqs = self.sqs.query("bool", filter=self.filters)
        for field in self.aggregations:
            agg_filters = self.applied_post_filters.copy()
            agg_filters.pop(field, None)
            filter_agg = A("filter", bool={"must": list(agg_filters.values())})
            filter_agg.bucket(field, "terms", field=field)
            self.sqs.aggs.bucket(field, filter_agg)

    def all(self):
        return self

    def none(self):
        self.broken_query = True
        return self

    @property
    def response(self):
        return self.get_response()

    def get_response(self):
        if self.broken_query:
            return EmtpyResponse()
        if not hasattr(self.sqs, "_response"):
            self.sqs = self.sqs.source(excludes=["*"])
        else:
            return self.sqs._response
        self.update_query()
        try:
            return self.sqs.execute()
        except Exception as e:
            logger.error("Elasticsearch error: %s", e)
            self.broken_query = True
            return EmtpyResponse()

    def add_aggregation(self, aggs):
        self.aggregations.extend(aggs)
        return self

    def add_date_histogram(self, date_field, interval="1y", format="yyyy"):
        a = A(
            "date_histogram",
            field=date_field,
            calendar_interval=interval,
            format=format,
        )
        self.sqs.aggs.bucket(date_field, a)
        return self

    def get_facet_data(self):
        if "aggregations" in self.response:
            return self.response["aggregations"]
        return {}

    def get_aggregations(self):
        if self.broken_query or "aggregations" not in self.response:
            return {"fields": {}}
        return {
            "fields": {
                k: [
                    [i["key"], i["doc_count"]]
                    for i in self.response["aggregations"][k][k]["buckets"]
                ]
                for k in self.response["aggregations"]
            }
        }

    def _make_query(self, *args, **kwargs):
        if kwargs:
            return Q("terms", **_make_values_lists(kwargs))
        return args[0]

    def filter(self, *args, **kwargs):
        query = self._make_query(*args, **kwargs)
        self.filters.append(query)
        return self

    def post_filter(self, name, *args, **kwargs):
        query = self._make_query(*args, **kwargs)
        self.post_filters.append(query)
        self.applied_post_filters[name] = query
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
        self.__class__ = type(qs.__class__.__name__, (self.__class__, qs.__class__), {})
        self.__dict__ = qs.__dict__
        self._qs = qs
        self._es_response = es_response
        self._es_map = {int(hit.meta.id): hit for hit in es_response}

    def __iter__(self):
        for obj in self._qs:
            hit = self._es_map[obj.pk]
            # mark_safe should work because highlight_options
            # has been set with encoder="html"
            obj.query_highlight = mark_safe(
                html.unescape(" [...] ".join(self._get_highlight(hit)))
            )
            yield obj

    def _get_highlight(self, hit):
        if hasattr(hit.meta, "highlight"):
            highlighted = set()
            highlight_count = 0
            for key in hit.meta.highlight:
                for snippet in hit.meta.highlight[key]:
                    for s in filter_highlight_snippet(snippet):
                        if not has_similar_match(s, highlighted):
                            highlight_count += 1
                            yield s

                        if highlight_count == 5:
                            return

                        highlighted.add(s)


def filter_highlight_snippet(snippet):
    """
    Split a highlight snippet into sections based on whitespace clusters
    and yields only those sections that contain <em> tags but are not fully
    enclosed by them.
    """
    # Cluster of 2 or more whitespace characters
    whitespace_cluster = re.compile(r"\s{2,}")

    sections = whitespace_cluster.split(snippet)

    for s in sections:
        if "<em>" in s and not (s.startswith("<em>") and s.endswith("</em>")):
            yield s


def has_similar_match(word, possibilities, cutoff=0.9):
    """
    Return True if `word` is close to any string in `possibilities`
    with a similarity >= `cutoff`.

    Implementation inspired by difflib.get_close_matches:
    https://github.com/python/cpython/blob/3.13/Lib/difflib.py#L=666
    """
    s = difflib.SequenceMatcher(isjunk=lambda c: c in " \r\n\t")
    s.set_seq2(word)

    for x in possibilities:
        s.set_seq1(x)
        if (
            s.real_quick_ratio() >= cutoff
            and s.quick_ratio() >= cutoff
            and s.ratio() >= cutoff
        ):
            return True

    return False
