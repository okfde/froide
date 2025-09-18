from django.conf import settings

from django_elasticsearch_dsl import Index
from elasticsearch_dsl import analyzer, tokenizer

from froide.helper.utils import get_module_attr_from_dotted_path

from .queryset import SearchQuerySetWrapper
from .registry import search_registry
from .signal_processor import CelerySignalProcessor

__all__ = [
    "CelerySignalProcessor",
    "search_registry",
    "SearchQuerySetWrapper",
]


def get_index(name):
    index_name = "%s_%s" % (settings.ELASTICSEARCH_INDEX_PREFIX, name)
    # if settings.ELASTICSEARCH_INDEX_PREFIX == 'froide_test':
    #     index_name += '_%s' % threading.get_ident()
    index = Index(index_name)

    # See Elasticsearch Indices API reference for available settings
    index.settings(number_of_shards=1, number_of_replicas=0)
    return index


def get_default_text_analyzer():
    return analyzer(
        "froide_analyzer",
        tokenizer="standard",
        filter=[
            "lowercase",
            "asciifolding",
        ],
    )


def get_default_ngram_analyzer():
    return analyzer(
        "froide_ngram_analyzer",
        tokenizer=tokenizer(
            "froide_ngram_tokenzier",
            type="edge_ngram",
            min_gram=1,
            max_gram=15,
            token_chars=["letter", "digit"],
        ),
        filter=[
            "lowercase",
            "asciifolding",
        ],
    )


def get_default_query_preprocessor():
    from froide.helper.search.filters import BaseQueryPreprocessor

    return BaseQueryPreprocessor()


def get_func(config_name, default_func):
    def get_it():
        from django.conf import settings

        func_path = settings.FROIDE_CONFIG.get(config_name, None)
        if not func_path:
            return default_func()

        analyzer_func = get_module_attr_from_dotted_path(func_path)
        return analyzer_func()

    return get_it


get_text_analyzer = get_func("text_analyzer", get_default_text_analyzer)
get_search_analyzer = get_func("search_analyzer", get_default_text_analyzer)
get_search_quote_analyzer = get_func("search_quote_analyzer", get_default_text_analyzer)
get_ngram_analyzer = get_func("ngram_analyzer", get_default_ngram_analyzer)
get_query_preprocessor = get_func("query_preprocessor", get_default_query_preprocessor)
