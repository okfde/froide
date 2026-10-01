#!/usr/bin/env python3
"""
Pre-commit hook to enforce named placeholders in translatable strings.

gettext versions disagree on whether unnamed placeholders like `{}` are
python-brace-format, so makemessages output would differ between machines.
"""

import ast
import string
import sys
from pathlib import Path

GETTEXT_FUNCTIONS = {
    "_",
    "gettext",
    "gettext_lazy",
    "gettext_noop",
    "ngettext",
    "ngettext_lazy",
    "pgettext",
    "pgettext_lazy",
    "npgettext",
    "npgettext_lazy",
}


def function_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def has_unnamed_placeholder(text: str) -> bool:
    try:
        return any(field == "" for _, field, _, _ in string.Formatter().parse(text))
    except ValueError:
        return False


def check_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors = []
    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.Call)
            or function_name(node) not in GETTEXT_FUNCTIONS
        ):
            continue
        for arg in node.args:
            # _("…{}…".format(x)): xgettext still extracts the literal
            if (
                isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Attribute)
                and arg.func.attr == "format"
            ):
                arg = arg.func.value
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and has_unnamed_placeholder(arg.value)
            ):
                errors.append(
                    f"{path}:{arg.lineno}: unnamed placeholder in {arg.value!r}, "
                    "use a named placeholder like {name} instead"
                )
    return errors


def main():
    errors = []
    for filename in sys.argv[1:]:
        errors.extend(check_file(Path(filename)))

    for error in errors:
        print(error)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
