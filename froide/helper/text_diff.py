from difflib import SequenceMatcher
import re

from django.utils.safestring import mark_safe
from django.utils.html import escape


SPLITTER = r'([^\w\-@/\.\:])'
SPLITTER_RE = re.compile(SPLITTER)
SPLITTER_MATCH_RE = re.compile('^%s$' % SPLITTER)


def get_diff_chunks(content):
    return [x for x in SPLITTER_RE.split(content) if x]


def is_diff_separator(s):
    return SPLITTER_MATCH_RE.match(s)


def get_differences_by_chunk(content_a, content_b):
    a_list = get_diff_chunks(content_a)
    b_list = get_diff_chunks(content_b)
    matcher = SequenceMatcher(
        None, a_list, b_list, autojunk=False
    )
    last_same = False
    for tag, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if i1 == i2:
            continue
        is_same = tag == 'equal'
        part = ''.join(a_list[i1:i2])
        if is_diff_separator(part):
            # Split chars should be ejected like the part before
            yield last_same, part
            continue
        last_same = is_same
        yield is_same, part


def get_differences(content_a, content_b, min_part_len=3):
    opened = False
    last_chunk = []
    for is_same, part in get_differences_by_chunk(content_a, content_b):
        long_enough = len(part) > min_part_len
        if is_same and opened and long_enough:
            if last_chunk:
                yield opened, ''.join(last_chunk)
                last_chunk = []
            opened = False
        elif not opened and not is_same:
            if last_chunk:
                yield opened, ''.join(last_chunk)
                last_chunk = []
            opened = True
        last_chunk.append(part)

    if last_chunk:
        yield opened, ''.join(last_chunk)


def get_tagged_differences(content_a, content_b,
        start_tag='<span {attrs}>',
        end_tag='</span>',
        attrs=None,
        min_part_len=3):

    if attrs is None:
        attrs = ''
    start_tag = start_tag.format(attrs=attrs)

    diff_chunks = get_differences(
        content_a, content_b,
        min_part_len=min_part_len
    )

    for redacted, part in diff_chunks:
        if redacted:
            yield start_tag
        yield escape(part)
        if redacted:
            yield end_tag


def mark_differences(content_a, content_b,
        start_tag='<span {attrs}>',
        end_tag='</span>',
        attrs=None):
    difference_tagger = get_tagged_differences(
        content_a, content_b,
        start_tag=start_tag, end_tag=end_tag,
        attrs=attrs
    )
    return mark_safe(''.join(difference_tagger))
