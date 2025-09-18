from unittest.mock import MagicMock

from froide.helper.search.filters import BaseSearchFilterSet


class DummyModel:
    pass


class DummyQS:
    def __init__(self):
        self.model = DummyModel()
        self.query = None

    def set_query(self, q):
        self.query = q
        return self


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
