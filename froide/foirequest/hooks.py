from collections import defaultdict, OrderedDict


class HookRegistry():
    def __init__(self):
        self.hooks = defaultdict(OrderedDict)

    def register(self, name, func):
        self.hooks[name][func] = True

    def run_hook(self, name, *args, **kwargs):
        for hook in self.hooks[name]:
            kwargs = hook(*args, **kwargs)
        return kwargs


registry = HookRegistry()
