from collections import defaultdict, OrderedDict
from typing import Callable


class HookRegistry:
    def __init__(self):
        self.hooks = defaultdict(OrderedDict)

    def register(self, name: str, func: Callable):
        self.hooks[name][func] = True

    def run_hook(self, name: str, *args, **kwargs):
        return_val = None
        for hook in self.hooks[name]:
            result = hook(*args, **kwargs)
            if result is not None:
                return_val = result
        return return_val


registry = HookRegistry()
