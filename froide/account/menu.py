from collections import defaultdict, namedtuple
from typing import DefaultDict, List

from django.http import HttpRequest

MenuItem = namedtuple("MenuItem", "section order label url")


def menu_order(item: MenuItem) -> int:
    return item.order


class MenuRegistry(object):
    def __init__(self):
        self.callbacks = []

    def register(self, func):
        self.callbacks.append(func)

    def get_menu_items(self, request: HttpRequest) -> DefaultDict[str, List[MenuItem]]:
        if request is None:
            return
        sections = defaultdict(list)
        for callback in self.callbacks:
            menu_item = callback(request)
            if menu_item is None:
                continue
            sections[menu_item.section].append(menu_item)
        for section in sections:
            sections[section] = sorted(sections[section], key=menu_order)
        return sections


menu_registry = MenuRegistry()
