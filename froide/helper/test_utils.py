import os


def skip_if_environ(name):
    if name in os.environ:
        def skip_inner(func):
            return lambda x: None
        return skip_inner

    def inner(func):
        return func
    return inner
