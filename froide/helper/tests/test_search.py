from unittest.mock import MagicMock

from django.utils.safestring import SafeString

import pytest

from froide.helper.search.filters import BaseSearchFilterSet
from froide.helper.search.queryset import ESQuerySetWrapper
from froide.helper.tests.testdata.search_highlights import search_highlight_tests


class DummyModel:
    pass


class DummyQS:
    def __init__(self, objs=None):
        self._objs = objs
        self.model = DummyModel()
        self.query = None

    def set_query(self, q):
        self.query = q
        return self

    def __iter__(self):
        return iter(self._objs)


class DummyHitMeta:
    def __init__(self, id, highlight=None):
        self.id = id
        self.highlight = highlight or {}


class DummyHit:
    def __init__(self, id, highlight=None):
        self.meta = DummyHitMeta(id, highlight)


class DummyObj:
    def __init__(self, pk):
        self.pk = pk
        self.query_highlight = None


class TestBaseSearchFilterSetQueryPreprocessing:
    def test_auto_query_without_query_value(self):
        qs = DummyQS()
        fs = BaseSearchFilterSet(queryset=qs)

        result = fs.auto_query(qs, "q", "")

        assert result is qs
        assert result.query is None

    def test_auto_query_with_default_query_preprocessor(self):
        qs = DummyQS()
        fs = BaseSearchFilterSet(queryset=qs)

        result = fs.auto_query(qs, "q", "test query")

        assert result is qs
        assert result.query is not None
        assert result.query.query == "test query"

    def test_auto_query_with_custom_query_preprocessor(self, monkeypatch):
        # Mock custom query preprocessor.
        mock_preprocessor = MagicMock()
        mock_preprocessor.prepare_query.return_value = "processed query"
        monkeypatch.setattr(
            "froide.helper.search.filters.get_query_preprocessor",
            lambda: mock_preprocessor,
        )

        qs = DummyQS()
        fs = BaseSearchFilterSet(queryset=qs)

        result = fs.auto_query(qs, "q", "original query")

        assert result.query.query == "processed query"
        mock_preprocessor.prepare_query.assert_called_once_with("original query")


@pytest.mark.parametrize(
    "highlight_list, query_highlight",
    search_highlight_tests,
    ids=[x[1][:20] for x in search_highlight_tests],
)
def test_es_queryset_wrapper_iter_highlight(highlight_list, query_highlight):
    """Test that highlights in search results are processed correctly."""
    obj = DummyObj(1)
    hit = DummyHit(1, {"field": highlight_list})
    qs = DummyQS([obj])
    es_response = [hit]

    wrapper = ESQuerySetWrapper(qs, es_response)
    result = list(wrapper)

    assert isinstance(result[0].query_highlight, SafeString)
    assert result[0].query_highlight == query_highlight


def test_es_queryset_wrapper_iter_no_highlight():
    """Test that absence of highlights results in empty string."""
    obj = DummyObj(2)
    hit = DummyHit(2)
    qs = DummyQS([obj])
    es_response = [hit]

    wrapper = ESQuerySetWrapper(qs, es_response)
    result = list(wrapper)

    assert result[0].query_highlight == ""
