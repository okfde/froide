# -*- coding: utf-8 -*-
import re

try:
    from html.entities import name2codepoint
except ImportError:
    from htmlentitydefs import name2codepoint

from django.utils.six import text_type as str
from django.utils.safestring import mark_safe
from django.utils.html import escape

from lxml import html
from lxml.html.clean import clean_html


def strip_all_tags(html_string):
    tree = html.document_fromstring(html_string)
    tree = clean_html(tree)
    return tree.xpath('//body')[0].text_content().strip()


##
# From http://effbot.org/zone/re-sub.htm#unescape-html
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.

def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is
    return re.sub("&#?\w+;", fixup, text)


def shorten_text(text, quote_prefix=u">", separators=None,
                 wrapper_start=u'<a href="#" class="show-text">…</a><div class="hidden-text">',
                 wrapper_end='</div>'):
    if separators is None:
        separators = [re.compile('\s*-{5}\w+ \w+-{5}\s*', re.UNICODE), re.compile(r'^--\s*$')]
    lines = []
    hidden = []
    hide_rest = False
    text_lines = text.splitlines()
    for i, line in enumerate(text_lines):
        for qs in separators:
            if qs.match(line) is not None:
                hidden.extend(text_lines[i:])
                hide_rest = True
                break
        if hide_rest:
            break
        if line.strip().startswith(quote_prefix):
            hidden.append(line)
            lines.append(None)
            continue
        lines.append(line)
        hidden.append(None)

    new_text = []
    hiding = False
    for i, hidden_line in enumerate(hidden):
        if hidden_line is None:
            if hiding:
                hiding = False
                new_text.append(wrapper_end)
            new_text.append(escape(lines[i]))
        else:
            if not hiding:
                new_text.append(wrapper_start)
                hiding = True
            new_text.append(escape(hidden_line))
    if hiding:
        new_text.append(wrapper_end)

    return mark_safe(u"\n".join(new_text))

EMAIL_NAME_RE = re.compile(r'<[^\s]+@[^\s]+>')


def replace_email_name(text, replacement=u""):
    return EMAIL_NAME_RE.sub(str(replacement), text)

EMAIL_RE = re.compile(r'[^\s]+@[^\s]+')


def replace_email(text, replacement=u""):
    return EMAIL_RE.sub(str(replacement), text)
