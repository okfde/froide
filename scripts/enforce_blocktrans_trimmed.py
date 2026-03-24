#!/usr/bin/env python3
"""
Pre-commit hook to enforce that blocktrans/blocktranslate blocks
whose body starts with a newline use the ``trimmed`` keyword.

A leading newline typically means the block is indented for
readability and the whitespace is unintentional. Blocks where
content starts on the same line as the opening tag are left alone,
since any inner newlines are likely intentional (e.g. in emails).

The ``trimmed`` keyword is inserted directly after the tag name,
before any other arguments (e.g. ``with``).

If any file is modified, the hook exits with a non-zero status
so pre-commit re-stages the fixed files.
"""

import re
import sys
from pathlib import Path

BLOCK_PATTERN = re.compile(
    r"""
    (\{%-?\s*(?:blocktrans|blocktranslate)\b)    # opening tag incl. keyword
    (.*?)                                        # arguments (with, count, …)
    (-?%\})                                      # close of opening tag
    (.*?)                                        # block body
    (\{%-?\s*(?:endblocktrans|endblocktranslate)\s*-?%\})  # end tag
    """,
    re.VERBOSE | re.DOTALL,
)


def fix_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")

    def replacer(match: re.Match) -> str:
        opening = match.group(1)
        args = match.group(2)
        close = match.group(3)
        body = match.group(4)
        end_tag = match.group(5)

        if "trimmed" in args or not body.startswith("\n"):
            return match.group(0)

        return opening + " trimmed" + args + close + body + end_tag

    updated = BLOCK_PATTERN.sub(replacer, original)

    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True

    return False


def main():
    changed = False
    for filename in sys.argv[1:]:
        path = Path(filename)
        if fix_file(path):
            print(f"Fixed {filename}")
            changed = True

    if changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
