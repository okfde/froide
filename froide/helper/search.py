import importlib

from django.conf import settings
from django.utils.http import urlencode
from django.urls import reverse

from django_elasticsearch_dsl import Index
from django_elasticsearch_dsl.signals import RealTimeSignalProcessor

from elasticsearch_dsl import analyzer, tokenizer, A
from elasticsearch_dsl.query import Q

from .tasks import (
    search_instance_save, search_instance_pre_delete,
    search_instance_delete
)


def get_index(name):
    index = Index('%s_%s' % (
        settings.ELASTICSEARCH_INDEX_PREFIX,
        name
    ))

    # See Elasticsearch Indices API reference for available settings
    index.settings(
        number_of_shards=1,
        number_of_replicas=0
    )
    return index


def get_pagination_vars(data):
    d = data.copy()
    d.pop('page', None)
    return '&' + urlencode(d)


def get_default_text_analyzer():
    return analyzer(
        'froide_analyzer',
        tokenizer='standard',
        filter=[
            'standard',
            'lowercase',
            'asciifolding',
        ]
    )


def get_default_ngram_analyzer():
    return analyzer(
        'froide_ngram_analyzer',
        tokenizer=tokenizer(
            'froide_ngram_tokenzier',
            type='edge_ngram',
            min_gram=1,
            max_gram=15,
            token_chars=['letter', 'digit']
        ),
        filter=[
            'standard',
            'lowercase',
            'asciifolding',
        ]
    )


def get_func(config_name, default_func):
    def get_it():
        from django.conf import settings
        func_path = settings.FROIDE_CONFIG.get(config_name, None)
        if not func_path:
            return default_func()

        module, func = func_path.rsplit('.', 1)
        module = importlib.import_module(module)
        analyzer_func = getattr(module, func)
        return analyzer_func()
    return get_it


get_text_analyzer = get_func('search_text_analyzer', get_default_text_analyzer)
get_ngram_analyzer = get_func('search_ngram_analyzer', get_default_ngram_analyzer)


def make_filter_url(url_name, data, get_active_filters=None):
    data = dict(data)
    url_kwargs = {}

    if get_active_filters is None:
        active_filters = {}
    else:
        active_filters = get_active_filters(data)

    for key in active_filters:
        url_kwargs[key] = data.pop(key)

    query_string = ''
    data = {k: v for k, v in data.items() if v}
    if data:
        query_string = '?' + urlencode(data)
    return reverse(url_name, kwargs=url_kwargs) + query_string


def get_facet_with_label(info, model=None, attr='name'):
    pks = [item['key'] for item in info['buckets']]
    objs = {
        o.pk: o for o in model.objects.filter(pk__in=pks)
    }
    for item in info['buckets']:
        yield {
            'label': getattr(objs[item['key']], attr),
            'id': item['key'],
            'count': item['doc_count']
        }


def resolve_facet(data, getter, model=None, make_url=None):
    def resolve(key, info):
        if model is not None:
            pks = [item['key'] for item in info['buckets']]
            objs = {
                o.pk: o for o in model.objects.filter(pk__in=pks)
            }
            for item in info['buckets']:
                item['object'] = objs[item['key']]
        for item in info['buckets']:
            item['active'] = getter(item['object']) == data.get(key)
            d = data.copy()
            d[key] = getter(item['object'])
            item['url'] = make_url(d)
            d.pop(key)
            item['clear_url'] = make_url(d)
        return info
    return resolve


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
        self._response = None

    def count(self):
        return self.response.hits.total

    def to_queryset(self):
        return self.sqs.to_queryset()

    def update_query(self):
        if self.filters:
            self.sqs.post_filter = Q('bool', must=self.filters)

    def all(self):
        return self

    @property
    def response(self):
        if not hasattr(self.sqs, '_response'):
            self.sqs = self.sqs.source(excludes=['*'])
        return self.sqs.execute()

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
        return {'fields': {
            k: [
                [i['key'], i['doc_count']]
                for i in self.response['aggregations'][k]['buckets']
            ]
            for k in self.response['aggregations']
        }}

    def filter(self, *args, **kwargs):
        if kwargs:
            value = Q('term', **kwargs)
        else:
            value = args[0]
        self.filters.append(value)
        self.update_query()
        return self

    def set_query(self, q):
        self.query = q
        self.sqs = self.sqs.query(self.query)
        return self

    def __getitem__(self, key):
        self.sqs = self.sqs[key]
        return self

    def __iter__(self):
        return iter(self.sqs)


class CelerySignalProcessor(RealTimeSignalProcessor):
    def handle_save(self, sender, instance, **kwargs):
        """Handle save.

        Given an individual model instance, update the object in the index.
        Update the related objects either.
        """
        search_instance_save.delay(instance)

    def handle_pre_delete(self, sender, instance, **kwargs):
        """Handle removing of instance object from related models instance.
        We need to do this before the real delete otherwise the relation
        doesn't exists anymore and we can't get the related models instance.
        """
        search_instance_pre_delete.delay(instance)

    def handle_delete(self, sender, instance, **kwargs):
        """Handle delete.

        Given an individual model instance, delete the object from index.
        """
        search_instance_delete.delay(instance)
