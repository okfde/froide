
from difflib import SequenceMatcher
import re

from django.utils.safestring import mark_safe
from django.utils.html import escape


SPLITTER = r'([^\w\-@/])'
SPLITTER_RE = re.compile(SPLITTER)
SPLITTER_MATCH_RE = re.compile('^%s$' % SPLITTER)


def full_tag_check(content, last_start_tag):
    for x in content[(last_start_tag + 1):]:
        if x.strip():
            return True
    return False


def get_differences_by_chunk(content_a, content_b):
    a_list = SPLITTER_RE.split(content_a)
    b_list = SPLITTER_RE.split(content_b)
    matcher = SequenceMatcher(
        None, a_list, b_list, autojunk=False
    )
    last_same = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if i1 == i2:
            continue
        is_same = tag == 'equal'
        part = ''.join(a_list[i1:i2])
        if SPLITTER_MATCH_RE.match(part):
            # Split chars should be ejected like the part before
            yield last_same, part
            continue
        last_same = is_same
        yield is_same, part


def mark_differences(content_a, content_b,
        start_tag='<span{attrs}>',
        end_tag='</span>',
        attrs=None,
        min_part_len=3):
    if attrs is None:
        attrs = ' class="redacted"'
    start_tag = start_tag.format(attrs=attrs)
    opened = False
    new_content = []
    last_start_tag = None
    for is_same, part in get_differences_by_chunk(content_a, content_b):
        long_enough = len(part) > min_part_len
        if is_same and opened and long_enough:
            if full_tag_check(new_content, last_start_tag):
                new_content.append(end_tag)
            else:
                new_content = new_content[:last_start_tag]
            opened = False
        if not opened and not is_same:
            opened = True
            last_start_tag = len(new_content)
            new_content.append(start_tag)
        new_content.append(escape(part))

    if opened:
        if full_tag_check(new_content, last_start_tag):
            new_content.append(end_tag)
        else:
            new_content = new_content[:last_start_tag]

    return mark_safe(''.join(new_content))
