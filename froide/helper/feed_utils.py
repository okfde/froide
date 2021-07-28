import re

CONTROLCHARS_RE = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]')


def clean_feed_output(func):
    def inner(self, arg):
        result = func(self, arg)
        return CONTROLCHARS_RE.sub('', result)
    return inner
