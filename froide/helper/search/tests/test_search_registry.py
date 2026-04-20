from django.http import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from froide.helper.search.registry import SearchItem, SearchRegistry


def test_no_duplicates():
    registry = SearchRegistry()

    def add_search(request) -> SearchItem:
        return {
            "name": "foirequest",
            "title": _("Requests"),
            "url": reverse("foirequest-list"),
        }

    def add_empty_search(request):
        return None

    r = HttpRequest()

    registry.register(add_search, "foirequest")
    assert len(registry.searches) == 1
    assert len(registry.get_searches(r)) == 1

    # doesn't get added twice
    registry.register(add_search, "foirequest")
    assert len(registry.searches) == 1
    assert len(registry.get_searches(r)) == 1

    # but works with different name
    registry.register(add_search, "document")
    assert len(registry.searches) == 2
    assert len(registry.get_searches(r)) == 2

    registry.register(add_empty_search, "empty")
    assert len(registry.searches) == 3
    assert len(registry.get_searches(r)) == 2

    # or without a name
    registry.register(add_search)
    assert len(registry.searches) == 4
    assert len(registry.get_searches(r)) == 3
