import logging

from haystack.fields import NgramField
from haystack.exceptions import MissingDependency

try:

    from haystack.backends.elasticsearch2_backend import (
        Elasticsearch2SearchEngine, Elasticsearch2SearchBackend
    )
    from haystack.backends.elasticsearch_backend import FIELD_MAPPINGS
except (ImportError, MissingDependency) as e:
    logging.warning(e)
else:

    class SuggestField(NgramField):  # noqa
        field_type = 'suggest'

    FIELD_MAPPINGS['suggest'] = {'type': 'string', 'analyzer': 'suggest_analyzer'}

    class FroideElasticsearch2SearchBackend(Elasticsearch2SearchBackend):
        # Settings to add an custom suggest analyzer
        DEFAULT_SETTINGS = {
            'settings': {
                "analysis": {
                    "analyzer": {
                        "ngram_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["haystack_ngram", "lowercase"]
                        },
                        "edgengram_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["haystack_edgengram", "lowercase"]
                        },
                        "suggest_analyzer": {
                            "filter": ["lowercase", "asciifolding"],
                            "type": "custom",
                            "tokenizer": "froide_autocomplete_ngram"
                        }
                    },
                    "tokenizer": {
                        "haystack_ngram_tokenizer": {
                            "type": "nGram",
                            "min_gram": 3,
                            "max_gram": 15,
                        },
                        "haystack_edgengram_tokenizer": {
                            "type": "edgeNGram",
                            "min_gram": 2,
                            "max_gram": 15,
                            "side": "front"
                        },
                        "froide_autocomplete_ngram": {
                            "type": "edgeNGram",
                            "min_gram": 1,
                            "max_gram": 15,
                            "token_chars": ["letter", "digit"]
                        }
                    },
                    "filter": {
                        "haystack_ngram": {
                            "type": "nGram",
                            "min_gram": 3,
                            "max_gram": 15
                        },
                        "haystack_edgengram": {
                            "type": "edgeNGram",
                            "min_gram": 2,
                            "max_gram": 15
                        }
                    }
                }
            }
        }

    class FroideElasticsearch2SearchEngine(Elasticsearch2SearchEngine):
        backend = FroideElasticsearch2SearchBackend
