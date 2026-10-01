import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts" / "enforce_blocktrans_trimmed.py"


@pytest.fixture(scope="module")
def fix_file():
    spec = importlib.util.spec_from_file_location("enforce_blocktrans_trimmed", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fix_file


def run(fix_file, tmp_path, content):
    template = tmp_path / "template.html"
    template.write_text(content)
    fix_file(template)
    return template.read_text()


def test_adds_trimmed_when_argument_only_contains_the_word(fix_file, tmp_path):
    result = run(
        fix_file,
        tmp_path,
        "{% blocktrans with t=trimmed_text %}\n  {{ t }}\n{% endblocktrans %}",
    )
    assert result.startswith("{% blocktrans trimmed with t=trimmed_text %}")


@pytest.mark.parametrize("line_end", ["  \n", "\t\n"])
def test_adds_trimmed_when_whitespace_precedes_newline(fix_file, tmp_path, line_end):
    result = run(
        fix_file,
        tmp_path,
        "{% blocktrans %}" + line_end + "  text\n{% endblocktrans %}",
    )
    assert result.startswith("{% blocktrans trimmed %}")


def test_keeps_block_with_existing_trimmed(fix_file, tmp_path):
    content = "{% blocktrans trimmed %}\n  text\n{% endblocktrans %}"
    assert run(fix_file, tmp_path, content) == content


def test_keeps_block_starting_on_tag_line(fix_file, tmp_path):
    content = "{% blocktrans %} text\n  more{% endblocktrans %}"
    assert run(fix_file, tmp_path, content) == content
