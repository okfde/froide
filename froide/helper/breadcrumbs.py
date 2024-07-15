from __future__ import annotations

import dataclasses
from typing import Iterator, Optional, Sequence, Tuple, Union

from django.template.context import Context
from django.urls import reverse
from django.views import View

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
    will be REVERSED to the link, so you can provide path pattern names.

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
        if hasattr(self, "breadcrumbs"):
            # breadcrumbs in attributes are handled differently, see above
            items = [
                reverse_breadcrumb(normalize_breadcrumb(item))
                for item in self.breadcrumbs
            ]
            return Breadcrumbs(items=items)

        raise NotImplementedError("No breadcrumb provider implemented")


@dataclasses.dataclass
class BreadcrumbItem:
    # will be displayed as the link text
    title: str
    url: Optional[str] = None

    @property
    def has_link(self) -> bool:
        return bool(self.url)


@dataclasses.dataclass
class Breadcrumbs:
    """
    You shouldn't iterate over Breadcrumbs.items, but over Breadcrumbs directly.

    Example:

    breadcrumbs = Breadcrumbs(items=...)
    for breadcrumb in breadcrumbs:
        ...
    """

    items: BreadcrumbItems
    # background color of breadcrumbs
    color: Optional[str] = None
    # whether the breadcrumbs should overlay the following content
    overlay: Optional[bool] = False

    def __iter__(self) -> Iterator[BreadcrumbItem]:
        for item in self.items:
            if type(item) is str:
                yield BreadcrumbItem(title=item)
            elif type(item) is tuple and len(item) == 2:
                # convert title to str, in case it's a lazy translation object
                yield BreadcrumbItem(title=str(item[0]), url=item[1])
            else:
                # i.e. lazy translation objects
                yield BreadcrumbItem(title=str(item))

    def __len__(self):
        return len(self.items)

    def __add__(self, items: BreadcrumbItems):
        """
        Add items using the plus operator: breadcrumbs + [...]
        """
        return dataclasses.replace(self, items=self.items + items)

    @staticmethod
    def from_view(
        view: BreadcrumbView, context: Union[Context, dict[str, object]]
    ) -> Optional[Breadcrumbs]:
        if isinstance(view, BreadcrumbView):
            items = view.get_breadcrumbs(context)

            if isinstance(items, Breadcrumbs):
                return items

            return Breadcrumbs(items=[normalize_breadcrumb(item) for item in items])


def normalize_breadcrumb(breadcrumb: Union[str, BreadcrumbTuple]) -> BreadcrumbTuple:
    if type(breadcrumb) is tuple:
        return breadcrumb
    elif type(breadcrumb) is str:
        return (breadcrumb, None)

    raise TypeError("Breadcrumb must be either a tuple or a string")


def reverse_breadcrumb(breadcrumb: BreadcrumbTuple) -> BreadcrumbTuple:
    if type(breadcrumb[1]) is str:
        return (breadcrumb[0], reverse(breadcrumb[1]))

    return breadcrumb
