import logging

from haystack.fields import NgramField
from haystack.exceptions import MissingDependency


class SuggestField(NgramField):
    pass


try:

    from haystack.backends.elasticsearch2_backend import (
        Elasticsearch2SearchEngine, Elasticsearch2SearchBackend
    )
    from haystack.backends.elasticsearch_backend import FIELD_MAPPINGS
except (ImportError, MissingDependency) as e:
    logging.warn(e)
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


class SearchQuerySetWrapper(object):
    """
    Decorates a SearchQuerySet object using a generator for efficient iteration
    """
    def __init__(self, sqs, model):
        self.sqs = sqs
        self.model = model

    def count(self):
        return self.sqs.count()

    def __iter__(self):
        for result in self.sqs:
            yield result.object

    def __getitem__(self, key):
        if isinstance(key, int) and (key >= 0 or key < self.count()):
            # return the object at the specified position
            return self.sqs[key].object
        # Pass the slice/range on to the delegate
        return SearchQuerySetWrapper(self.sqs[key], self.model)
