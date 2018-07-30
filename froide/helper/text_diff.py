
from difflib import SequenceMatcher
import re

from django.utils.safestring import mark_safe
from django.utils.html import escape

ONLY_SPACE_LINE = re.compile('^[ \u00A0]+$', re.U | re.M)


def remove_space_lines(content):
    return ONLY_SPACE_LINE.sub('', content)


def mark_differences(content_a, content_b,
        start_tag='<span{attrs}>',
        end_tag='</span>',
        attrs=None,
        min_part_len=3):
    if attrs is None:
        attrs = ' class="redacted"'
    start_tag = start_tag.format(attrs=attrs)
    opened = False
    redact = False
    new_content = []
    matcher = SequenceMatcher(
        None, content_a, content_b, autojunk=False
    )
    last_start_tag = None

    full_tag_check = lambda content, last_start_tag: \
        [x for x in content[(last_start_tag + 1):] if x.strip()]

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        long_enough = i2 - i1 > min_part_len
        redact = tag != 'equal'
        if not redact and opened and long_enough:
            if full_tag_check(new_content, last_start_tag):
                new_content.append(end_tag)
            else:
                new_content = new_content[:last_start_tag]
            opened = False
        if not opened and redact:
            opened = True
            last_start_tag = len(new_content)
            new_content.append(start_tag)
        new_content.append(escape(remove_space_lines(content_a[i1:i2])))
    if opened:
        if full_tag_check(new_content, last_start_tag):
            new_content.append(end_tag)
        else:
            new_content = new_content[:last_start_tag]

    return mark_safe(''.join(new_content))
