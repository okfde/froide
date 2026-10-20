from pathlib import Path

import pytest

from froide.helper.redaction import redact_file

TEST_PDF = (
    Path(__file__).parent.parent.parent / "tests/testdata/redaction-test-cropbox.pdf"
)


def make_page_instructions(num_pages):
    return [{"width": 1000, "rects": [], "texts": []} for _ in range(num_pages)]


@pytest.mark.parametrize("num_pages", [0, 2])
def test_page_count_mismatch_is_redaction_error(num_pages):
    instructions = {"pages": make_page_instructions(num_pages)}

    with TEST_PDF.open("rb") as pdf_file:
        with pytest.raises(Exception) as excinfo:
            redact_file(pdf_file, instructions)

    assert not isinstance(excinfo.value, AssertionError)
