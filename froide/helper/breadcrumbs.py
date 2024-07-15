from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Generator, Optional, Sequence, Tuple, Union

from django.template.context import Context
from django.urls import NoReverseMatch, reverse
from django.views import View

logger = logging.getLogger(__name__)

BreadcrumbTuple = Tuple[str, Union[str, None]]
"""
First item: link text
Second item: link, or None
"""

BreadcrumbItems = Sequence[Union[str, BreadcrumbTuple]]


class BreadcrumbView(View):
    """
    Your view must either provide a `breadcrumbs` attribute, or a
    `get_breadcrumbs` method.

    The `breadcrumbs` attribute is a sequence of strings or tuples,
    e.g. ["Just text", ("A link", "url-pattern-name")].
    The first element of the tuple specifies the link text, the second one
    will be REVERSED to the link, so you can provide path names.

    Using the `get_breadcrumbs` method, you can provide breadcrumbs as
    above, with the difference that urls WILL NOT BE REVERSED.
    You can also directly return a `Breadcrumbs` instance.

    Example implementation:

    class MyView(BreadcrumbView):
        def get_breadcrumbs():
            return [("Foo", "/foo/"), "Bar"]
    """

    breadcrumbs: Optional[BreadcrumbItems]

    def get_breadcrumbs(self) -> Union[BreadcrumbItems, Breadcrumbs]:
        raise NotImplementedError("No breadcrumb provider implemented")


@dataclass
class BreadcrumbItem:
    # will be displayed as the link text
    title: str
    url: Optional[str] = None
    # whether the breadcrumbs should overlay the following content
    overlay: Optional[bool] = False

    @property
    def has_link(self) -> bool:
        return bool(self.url)


@dataclass
class Breadcrumbs:
    items: BreadcrumbItems
    color: Optional[str] = None

    def __iter__(self) -> Generator[BreadcrumbItem]:
        for item in self.items:
            if type(item) is str:
                yield BreadcrumbItem(title=item)
            elif type(item) is tuple and len(item) == 2:
                yield BreadcrumbItem(title=item[0], url=item[1])
            else:
                # i.e. lazy translation objects
                yield BreadcrumbItem(title=str(item))

    def __len__(self):
        return len(self.items)

    def __add__(self, items: BreadcrumbItems):
        """
        Add items using the plus operator: breadcrumbs + [...]
        """
        self.items += items
        return self

    @staticmethod
    def from_view(
        view: BreadcrumbView, context: Union[Context, dict[str, object]]
    ) -> Optional[Breadcrumbs]:
        if hasattr(view, "get_breadcrumbs") and callable(view.get_breadcrumbs):
            items = view.get_breadcrumbs(context)

            if isinstance(items, Breadcrumbs):
                return items

            return Breadcrumbs(items=[normalize_breadcrumb(item) for item in items])

        if hasattr(view, "breadcrumbs"):
            items = [
                reverse_breadcrumb(normalize_breadcrumb(item))
                for item in view.breadcrumbs
            ]
            return Breadcrumbs(items=items)


def normalize_breadcrumb(breadcrumb: Union[str, BreadcrumbTuple]) -> BreadcrumbTuple:
    if type(breadcrumb) is tuple:
        return breadcrumb
    elif type(breadcrumb) is str:
        return (breadcrumb, None)

    logger.error("Received breadcrumb that is neither a tuple nor a string", breadcrumb)


def reverse_breadcrumb(breadcrumb: BreadcrumbTuple) -> BreadcrumbTuple:
    if type(breadcrumb[1]) is str:
        try:
            return (breadcrumb[0], reverse(breadcrumb[1]))
        except NoReverseMatch:
            logger.error("Breadcrumb url could not be reversed", breadcrumb)
            return (breadcrumb[0], None)

    return breadcrumb
