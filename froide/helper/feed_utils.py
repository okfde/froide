import re

from django.utils.safestring import SafeString, mark_safe

CONTROLCHARS_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")


def clean_feed_output(func):
    def inner(self, arg):
        result = func(self, arg)
        is_safe = isinstance(result, SafeString)
        result = CONTROLCHARS_RE.sub("", result)
        if is_safe:
            result = mark_safe(result)
        return result

    return inner
