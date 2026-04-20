from typing import Callable, NotRequired, Optional, TypedDict

from django.http import HttpRequest

from django_stubs_ext import StrOrPromise


class SearchItem(TypedDict):
    name: str
    title: StrOrPromise
    url: StrOrPromise
    menu_title: NotRequired[StrOrPromise]
    order: NotRequired[int]


type SearchResponse = SearchItem | None
type SearchItemCallback = Callable[[HttpRequest], SearchResponse]


class SearchRegistry(object):
    def __init__(self):
        self.named_searches: set[str] = set()
        self.searches: list[SearchItemCallback] = []

    # TODO: in the next breaking release, make `name` required
    def register(self, func: SearchItemCallback, name: Optional[str] = None):
        if name in self.named_searches:
            return

        if name:
            self.named_searches.add(name)

        self.searches.append(func)

    def get_searches(self, request: HttpRequest) -> list[SearchItem]:
        sections: list[SearchItem] = []
        for callback in self.searches:
            if menu_item := callback(request):
                sections.append(menu_item)

        return sorted(sections, key=lambda x: (x.get("order", 5), x["title"]))


search_registry = SearchRegistry()
