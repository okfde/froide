import importlib

from django.conf import settings
from django.db import models
from django.utils.http import urlencode
from django.urls import reverse
from django.core.paginator import Paginator
from django.utils.safestring import mark_safe

from django_elasticsearch_dsl import Index
from django_elasticsearch_dsl.registries import registry
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


def make_filter_url(url_name, data=None, get_active_filters=None):
    if data is None:
        data = {}
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


def key_getter(item):
    return item['key']


def resolve_facet(data, getter=None, label_getter=None,
                  model=None, make_url=None):
    if getter is None:
        getter = key_getter

    if label_getter is None:
        label_getter = key_getter

    def resolve(key, info):
        if model is not None:
            pks = [item['key'] for item in info['buckets']]
            objs = {
                o.pk: o for o in model.objects.filter(pk__in=pks)
            }
            for item in info['buckets']:
                item['object'] = objs[item['key']]
        for item in info['buckets']:
            item['active'] = getter(item) == data.get(key)
            item['label'] = label_getter(item)
            d = data.copy()
            d[key] = getter(item)
            item['url'] = make_url(d)
            d.pop(key)
            item['clear_url'] = make_url(d)
        return info
    return resolve


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

    def count(self):
        return self.response.hits.total

    def to_queryset(self):
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
        if not hasattr(self.sqs, '_response'):
            self.sqs = self.sqs.source(excludes=['*'])
        try:
            return self.sqs.execute()
        except Exception:
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
            obj.es_highlight = mark_safe(' '.join(self._get_highlight(hit)))
            yield obj

    def _get_highlight(self, hit):
        if hasattr(hit.meta, 'highlight'):
            for key in hit.meta.highlight:
                yield from hit.meta.highlight[key]


class ElasticsearchPaginator(Paginator):
    """
    Paginator that prevents two queries to ES (for count and objects)
    as ES gives count with objects
    """
    MAX_ES_OFFSET = 10000

    def page(self, number):
        """
        Returns a Page object for the given 1-based page number.
        """
        bottom = (number - 1) * self.per_page
        if bottom >= self.MAX_ES_OFFSET:
            # Only validate if bigger than offset
            number = self.validate_number(number)
            bottom = (number - 1) * self.per_page

        top = bottom + self.per_page
        self.object_list = self.object_list[bottom:top]

        # ignore top boundary
        # if top + self.orphans >= self.count:
        #     top = self.count

        # Validate number after limit/offset has been set
        number = self.validate_number(number)
        return self._get_page(self.object_list, number, self)


class CelerySignalProcessor(RealTimeSignalProcessor):
    def setup(self):
        for model in registry.get_models():
            models.signals.post_save.connect(self.handle_save, sender=model)
            models.signals.post_delete.connect(self.handle_delete, sender=model)

            models.signals.m2m_changed.connect(self.handle_m2m_changed, sender=model)
            models.signals.pre_delete.connect(self.handle_pre_delete, sender=model)

    def teardown(self):
        # Listen to all model saves.
        for model in registry.get_models():
            models.signals.post_save.disconnect(self.handle_save, sender=model)
            models.signals.post_delete.disconnect(self.handle_delete, sender=model)
            models.signals.m2m_changed.disconnect(self.handle_m2m_changed, sender=model)
            models.signals.pre_delete.disconnect(self.handle_pre_delete, sender=model)

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
