from collections import defaultdict, OrderedDict


class HookRegistry():
    def __init__(self):
        self.hooks = defaultdict(OrderedDict)

    def register(self, name, func):
        self.hooks[name][func] = True

    def run_hook(self, name, *args, **kwargs):
        return_val = None
        for hook in self.hooks[name]:
            result = hook(*args, **kwargs)
            if result is not None:
                return_val = result
        return return_val


registry = HookRegistry()
