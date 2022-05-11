import functools
import re
from html.entities import name2codepoint
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple, Union

from django.conf import settings
from django.utils.html import strip_tags
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _

from slugify import slugify as _slugify

try:
    from lxml import html as html_parser
    from lxml.html import HtmlElement
except ImportError:
    html_parser = None

    class HtmlElement:
        pass


SEPARATORS = re.compile(r"( *-{4,}\s*[\w ]+\s*-{4,}\s*|^--\s*$)", re.UNICODE | re.M)

SLUGIFY_REPLACEMENTS = getattr(settings, "SLUGIFY_REPLACEMENTS", ())


def slugify(s):
    return _slugify(s, replacements=SLUGIFY_REPLACEMENTS)


def unescape(text):
    """
    From http://effbot.org/zone/re-sub.htm#unescape-html
    Removes HTML or XML character references and entities from a text string.

    @param text The HTML (or XML) source text.
    @return The plain text, as a Unicode string, if necessary.
    """

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

    return re.sub(r"&#?\w+;", fixup, text)


def quote_text(text: str, prefix: str = "> ") -> str:
    return "\n".join(f"{prefix}{x}" for x in text.splitlines())


def split_text_by_separator(
    text: str, separator: Optional[Pattern[str]] = None
) -> List[str]:
    if separator is None:
        separator = SEPARATORS
    split_text = separator.split(text)
    split_point = 1
    for part in split_text[::2]:
        if not part.strip():
            split_point += 2
        else:
            break
    if len(split_text) == 1:
        split_text.append("")
    if len(split_text) > 2:
        split_text = [
            "".join(split_text[:split_point]),
            "".join(split_text[split_point:]),
        ]
    return split_text


Replacements = List[Union[Tuple[str, str], Tuple[Pattern[str], str]]]


def redact_user_strings(content: str, user_replacements: Replacements) -> str:
    for needle, repl in user_replacements:
        if isinstance(needle, str):
            content = replace_word(needle, repl, content)
        else:
            content = replace_custom(needle, repl, content)

    return content


def redact_subject(
    content: str, user_replacements: Optional[Replacements] = None
) -> str:
    if user_replacements:
        content = redact_user_strings(content, user_replacements)
    content = redact_content(content)
    return content[:255]


def redact_plaintext(
    content: Union[str, SafeString],
    redact_greeting: bool = False,
    redact_closing: bool = False,
    user_replacements: Optional[Replacements] = None,
    replacements: Optional[Dict[Union[str, Pattern[str]], str]] = None,
) -> str:
    content = redact_content(content)

    if redact_closing:
        content = remove_closing(content)
    if redact_greeting:
        greetings = settings.FROIDE_CONFIG.get("greetings")
        if greetings:
            greeting_replacement = str(_("<< Greeting >>"))
            content = replace_custom(greetings, greeting_replacement, content)

    if user_replacements:
        content = redact_user_strings(content, user_replacements)

    if replacements is not None:
        for key, val in replacements.items():
            if isinstance(key, re.Pattern):
                content = key.sub(val, content)
            else:
                content = content.replace(key, val)

    return content


def redact_content(content: Union[str, SafeString]) -> str:
    content = replace_email_name(content, _("<<name and email address>>"))
    content = replace_email(content, _("<<email address>>"))

    if settings.FROIDE_CONFIG.get("custom_replacements"):
        content = replace_custom(
            settings.FROIDE_CONFIG["custom_replacements"],
            str(_("<<removed>>")),
            content,
        )
    return content


def replace_word(needle: str, replacement: str, content: str) -> str:
    if not needle:
        return content
    return re.sub(
        r"(^|[\W_])%s($|[\W_])" % re.escape(needle),
        "\\1%s\\2" % replacement,
        content,
        re.U | re.I,
    )


EMAIL = r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
EMAIL_RE = re.compile(EMAIL, flags=re.IGNORECASE)
EMAIL_NAME_RE = re.compile("<%s>" % EMAIL, flags=re.IGNORECASE)


def replace_email_name(text: str, replacement: str = "") -> str:
    return EMAIL_NAME_RE.sub(str(replacement), text)


def replace_email(text: str, replacement: str = "") -> str:
    return EMAIL_RE.sub(str(replacement), text)


def find_all_emails(text: str) -> List[Any]:
    return EMAIL_RE.findall(text)


def replace_custom(
    regex_list: Union[Pattern[str], List[Pattern[str]]],
    replacement: str,
    content: str,
) -> str:
    if isinstance(regex_list, re.Pattern):
        regex_list = [regex_list]
    for regex in regex_list:
        match = regex.search(content)
        if match is not None and len(match.groups()):
            content = content.replace(match.group(1), replacement)
    return content


def remove_part(
    regexes: List[Pattern[str]], content: str, func: Callable[[str, re.Match], str]
) -> str:
    for regex in regexes:
        match = regex.search(content)
        if match is not None:
            content = func(content, match)
            break
    return content


def remove_closing(content: str, regexes: Optional[List[Pattern[str]]] = None) -> str:
    if regexes is None:
        regexes = settings.FROIDE_CONFIG.get("closings", [])
    return remove_part(regexes, content, func=lambda c, m: c[: m.end()].strip())


def remove_closing_inclusive(content: str) -> str:
    regexes = settings.FROIDE_CONFIG.get("closings", [])
    return remove_part(regexes, content, func=lambda c, m: c[: m.start()].strip())


def remove_greeting_inclusive(content: str) -> str:
    regexes = settings.FROIDE_CONFIG.get("greetings", [])
    return remove_part(regexes, content, func=lambda c, m: c[m.end() :].strip())


def ignore_tag(x: HtmlElement) -> str:
    return "%s%s" % (x.text_content(), x.tail if x.tail else "")


def make_strong(x: HtmlElement) -> str:
    return "**%s**%s" % (x.text_content(), x.tail if x.tail else "")


def make_italic(x: HtmlElement) -> str:
    return "*%s*%s" % (x.text_content(), x.tail if x.tail else "")


def make_link(x: HtmlElement) -> str:
    return "%s ( %s )%s" % (
        x.text_content(),
        x.attrib.get("href", ""),
        x.tail if x.tail else "",
    )


def make_heading(x: HtmlElement, num: int = 1) -> str:
    return "%s %s\n\n%s" % ("#" * num, x.text_content(), x.tail if x.tail else "")


def heading_maker(num: int) -> functools.partial:
    return functools.partial(make_heading, num=num)


def make_paragraph(el: HtmlElement) -> None:
    el.append(html_parser.Element("br"))
    convert_element(el)


HTML_CONVERTERS = {
    "a": make_link,
    "strong": make_strong,
    "b": make_strong,
    "i": make_italic,
    "em": make_italic,
    "p": make_paragraph,
    "h1": heading_maker(1),
    "h2": heading_maker(2),
    "h3": heading_maker(3),
    "h4": heading_maker(4),
    "h5": heading_maker(5),
    "h6": heading_maker(6),
    "br": lambda x: "\n%s" % (x.tail if x.tail else ""),
    "hr": lambda x: "\n\n%s\n\n%s" % ("-" * 25, x.tail if x.tail else ""),
}

HTML_GARBAGE = ("style",)


def convert_html_to_text(html_str: str, ignore_tags: None = None) -> str:
    """
    If lxml is available, convert to Markdown (but badly)
    otherwise just strip_tags
    """
    if not html_str:
        return ""
    if html_parser is None:
        return strip_tags(html_str)

    root = html_parser.fromstring(html_str)
    try:
        body = root.xpath("./body")[0]
    except IndexError:
        # No body element
        body = root

    for tag in HTML_GARBAGE:
        els = body.xpath(".//" + tag)
        for el in els:
            el.getparent().remove(el)

    convert_element(body, ignore_tags=ignore_tags)

    text = html_parser.tostring(
        body, pretty_print=True, method="text", encoding="utf-8"
    ).decode("utf-8")

    return "\n".join(x.strip() for x in text.splitlines()).strip()


def convert_element(
    root_element: HtmlElement, ignore_tags: Optional[Tuple[str]] = None
) -> None:
    if ignore_tags is None:
        ignore_tags = ()
    for tag, func in HTML_CONVERTERS.items():
        if tag in ignore_tags:
            func = ignore_tag
        els = root_element.xpath(".//" + tag)
        for el in els:
            replacement = func(el)
            if replacement is not None:
                repl_tag = html_parser.Element("span")
                repl_tag.text = replacement
                el.getparent().replace(el, repl_tag)
