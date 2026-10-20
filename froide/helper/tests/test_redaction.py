import io
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

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


def duplicate_pages_in_place(pdf_file, instructions):
    # Stand-in for rewrite_pdf: like Ghostscript, it overwrites the given file
    # and returns a new handle, but it doubles the page count
    reader = PdfReader(pdf_file.name)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
        writer.add_page(page)
    with open(pdf_file.name, "wb") as f:
        writer.write(f)
    return open(pdf_file.name, "rb")


def test_redaction_falls_back_when_rewrite_changes_page_count(monkeypatch):
    """
    Rewriting the PDF can change its page count, so it no longer matches the redaction
    instructions, which are based on the pages pdf.js shows in the browser. Redaction
    should then fall back to the original PDF instead of failing.
    """
    monkeypatch.setattr("froide.helper.redaction.rewrite_pdf", duplicate_pages_in_place)
    # Instructions match the original PDF, but not the rewritten one
    instructions = {"pages": make_page_instructions(1)}

    with TEST_PDF.open("rb") as pdf_file:
        pdf_bytes = redact_file(pdf_file, instructions)

    # One page means the original was used, not the rewritten PDF
    assert len(PdfReader(io.BytesIO(pdf_bytes)).pages) == 1
