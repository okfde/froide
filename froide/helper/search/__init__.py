import importlib

from django.conf import settings

from elasticsearch_dsl import analyzer, tokenizer

from django_elasticsearch_dsl import Index

from .signal_processor import CelerySignalProcessor
from .queryset import SearchQuerySetWrapper
from .registry import search_registry

__all__ = [
    'CelerySignalProcessor', 'search_registry', 'SearchQuerySetWrapper',
]


def get_index(name):
    index_name = '%s_%s' % (
        settings.ELASTICSEARCH_INDEX_PREFIX,
        name
    )
    # if settings.ELASTICSEARCH_INDEX_PREFIX == 'froide_test':
    #     index_name += '_%s' % threading.get_ident()
    index = Index(index_name)

    # See Elasticsearch Indices API reference for available settings
    index.settings(
        number_of_shards=1,
        number_of_replicas=0
    )
    return index


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
