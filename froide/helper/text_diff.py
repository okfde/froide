import re
from difflib import SequenceMatcher
from typing import Iterator, List, Optional, Tuple

from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe

SPLITTER = r"([\u0000-\u002C\u003B-\u003F\u005B-\u005e\u0060\u007B-\u007E])"
SPLITTER_RE = re.compile(SPLITTER)
SPLITTER_MATCH_RE = re.compile("^%s$" % SPLITTER)
CONTENT_CACHE_THRESHOLD = 5000


def get_diff_chunks(content: str) -> List[str]:
    """
    Split text into words and the separators between them.

    Separators are kept as their own chunks so the diff can align on word
    boundaries instead of individual characters.

    >>> get_diff_chunks("Hallo Max Mustermann!")
    ['Hallo', ' ', 'Max', ' ', 'Mustermann', '!']
    """
    return [x for x in SPLITTER_RE.split(content) if x]


def is_diff_separator(s: str) -> bool:
    """
    Is this chunk a single separator character (space, comma, ...)?

    >>> is_diff_separator(" "), is_diff_separator(","), is_diff_separator("Max")
    (True, True, False)
    """
    return bool(SPLITTER_MATCH_RE.match(s))


def get_differences_by_chunk(
    content_a: str, content_b: str
) -> Iterator[Tuple[bool, str]]:
    """
    Compare two texts chunk-wise, yielding `content_a` in runs.

    Yields ``(is_same, text)``, where the flag means *unchanged* — the opposite
    of the flag `get_differences` yields.

    Only `content_a` is ever yielded; `content_b` just decides which parts of it
    count as changed. Swapping the arguments yields the other text.

    >>> a = "Sehr geehrte Frau Meier, mein Name ist Max Mustermann."
    >>> b = "Sehr geehrte Frau Meier, mein Name ist <<Name>>."
    >>> list(get_differences_by_chunk(a, b))
    [(True, 'Sehr geehrte Frau Meier, mein Name ist '), (False, 'Max Mustermann.')]
    """
    a_list = get_diff_chunks(content_a)
    b_list = get_diff_chunks(content_b)
    matcher = SequenceMatcher(None, a_list, b_list, autojunk=False)
    last_same = False
    for tag, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if i1 == i2:
            continue
        is_same = tag == "equal"
        part = "".join(a_list[i1:i2])
        if is_diff_separator(part):
            # Split chars should be ejected like the part before
            yield last_same, part
            continue
        last_same = is_same
        yield is_same, part


def get_differences(
    content_a: str, content_b: str, min_part_len: int = 3
) -> Iterator[Tuple[bool, str]]:
    """
    Group the chunk-wise diff into runs of changed and unchanged text.

    Yields ``(is_changed, text)``, inverting the flag of
    `get_differences_by_chunk`.

    >>> a = "Kontakt: max@example.org oder Tel 030-12345"
    >>> b = "Kontakt: <<email address>> oder Tel 030-12345"
    >>> list(get_differences(a, b))
    [(False, 'Kontakt: '), (True, 'max@example.org'), (False, ' oder Tel 030-12345')]

    Unchanged runs shorter than `min_part_len` are swallowed by the surrounding
    changed run, keeping neighbouring changes in one block instead of breaking
    them apart at every space:

    >>> list(get_differences("Max A Mustermann", "<<N>> A <<M>>"))
    [(True, 'Max A Mustermann')]
    >>> list(get_differences("Max A Mustermann", "<<N>> A <<M>>", min_part_len=0))
    [(True, 'Max'), (False, ' A '), (True, 'Mustermann')]
    """
    opened = False
    last_chunk = []
    for is_same, part in get_differences_by_chunk(content_a, content_b):
        long_enough = len(part) > min_part_len
        if is_same and opened and long_enough:
            if last_chunk:
                yield opened, "".join(last_chunk)
                last_chunk = []
            opened = False
        elif not opened and not is_same:
            if last_chunk:
                yield opened, "".join(last_chunk)
                last_chunk = []
            opened = True
        last_chunk.append(part)

    if last_chunk:
        yield opened, "".join(last_chunk)


def get_tagged_differences(
    content_a: str,
    content_b: str,
    start_tag: str = "<span {attrs}>",
    end_tag: str = "</span>",
    attrs: Optional[str] = None,
    min_part_len: int = 3,
) -> Iterator[SafeString]:
    """
    Yield the diff as HTML pieces, wrapping changed runs in `start_tag`/`end_tag`.

    Text is escaped here, tags are not — hence the pieces are yielded separately
    rather than concatenated by the caller.

    >>> a = "Sehr geehrte Frau Meier, mein Name ist Max Mustermann."
    >>> b = "Sehr geehrte Frau Meier, mein Name ist <<Name>>."
    >>> list(get_tagged_differences(a, b, attrs='class="redacted"'))
    ['Sehr geehrte Frau Meier, mein Name ist ', '<span class="redacted">', 'Max Mustermann.', '</span>']
    """
    if attrs is None:
        attrs = ""
    start_tag = SafeString(start_tag.format(attrs=attrs))
    end_tag = SafeString(end_tag)

    diff_chunks = get_differences(content_a, content_b, min_part_len=min_part_len)

    for redacted, part in diff_chunks:
        if redacted:
            yield start_tag
        yield escape(part)
        if redacted:
            yield end_tag


def mark_differences(
    content_a: str,
    content_b: str,
    start_tag: str = "<span {attrs}>",
    end_tag: str = "</span>",
    attrs: Optional[str] = None,
) -> SafeString:
    """
    Render the diff of two texts as one HTML string.

    >>> a = "Sehr geehrte Frau Meier, mein Name ist Max Mustermann."
    >>> b = "Sehr geehrte Frau Meier, mein Name ist <<Name>>."
    >>> mark_differences(a, b, attrs='class="redacted"')
    'Sehr geehrte Frau Meier, mein Name ist <span class="redacted">Max Mustermann.</span>'

    Markup in the input is escaped, so it cannot break out of the span. Escaping
    happens per run, so a tag boundary can end up inside an escaped sequence:

    >>> mark_differences("a <b> c", "a <<x>> c", attrs='class="r"')
    'a &lt;<span class="r">b&gt; c</span>'
    """
    difference_tagger = get_tagged_differences(
        content_a, content_b, start_tag=start_tag, end_tag=end_tag, attrs=attrs
    )
    return mark_safe("".join(difference_tagger))
