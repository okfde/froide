# -*- coding: utf-8 -*-
import re

try:
    from html.entities import name2codepoint
except ImportError:
    from htmlentitydefs import name2codepoint

from django.utils.six import text_type as str, unichr as chr

SEPARATORS = re.compile(r'(\s*-{5}\w+ \w+-{5}\s*|^--\s*$)', re.UNICODE | re.M)


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
                    return chr(int(text[3:-1], 16))
                else:
                    return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = chr(name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is
    return re.sub("&#?\w+;", fixup, text)


def split_text_by_separator(text, separator=None):
    if separator is None:
        separator = SEPARATORS
    split_text = separator.split(text)
    if len(split_text) == 1:
        split_text.append('')
    if len(split_text) > 2:
        split_text = [split_text[0], '\n'.join(split_text[1:])]
    return split_text


def replace_word(needle, replacement, content):
    return re.sub('(^|\W)%s($|\W)' % re.escape(needle),
                    '\\1%s\\2' % replacement, content, re.U)


EMAIL_NAME_RE = re.compile(r'<[^\s]+@[^\s]+>')


def replace_email_name(text, replacement=u""):
    return EMAIL_NAME_RE.sub(str(replacement), text)

EMAIL_RE = re.compile(r'[^\s]+@[^\s]+')


def replace_email(text, replacement=u""):
    return EMAIL_RE.sub(str(replacement), text)


def replace_greetings(content, greetings, replacement):
    for greeting in greetings:
        match = greeting.search(content)
        if match is not None and len(match.groups()):
            content = content.replace(match.group(1),
                replacement)
    return content


def remove_closing(content, closings):
    for closing in closings:
        match = closing.search(content)
        if match is not None:
            content = content[:match.end()]
            break
    return content
