import io
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from wand.exceptions import WandError

from froide.helper import redaction
from froide.helper.redaction import redact_file

TESTDATA = Path(__file__).parent.parent.parent / "tests/testdata"
CROPBOX_PDF = TESTDATA / "redaction-test-cropbox.pdf"
ROTATED_PDF = TESTDATA / "redaction-test-rotated.pdf"


def make_page_instructions(num_pages, redacted_pages=()):
    return [
        {
            "width": 1000,
            "rects": [[0, 0, 1000, 1000]] if page_idx in redacted_pages else [],
            "texts": [],
        }
        for page_idx in range(num_pages)
    ]


def redact(pdf_path, page_instructions, password=None):
    instructions = {"pages": page_instructions}
    if password is not None:
        instructions["password"] = password
    with pdf_path.open("rb") as pdf_file:
        pdf_bytes = redact_file(pdf_file, instructions)
    return PdfReader(io.BytesIO(pdf_bytes))


def fail_rewrite(filename, password=None):
    return None


def keep_unchanged(filename, password=None):
    return filename


def repair_with(source_pdf):
    def repair(filename, password=None):
        Path(filename).write_bytes(source_pdf.read_bytes())
        return filename

    return repair


def fake_tools(monkeypatch, gs=fail_rewrite, cairo=fail_rewrite, qpdf=fail_rewrite):
    monkeypatch.setattr(redaction, "rewrite_pdf_in_place", gs)
    monkeypatch.setattr(redaction, "rewrite_hard_pdf_in_place", cairo)
    monkeypatch.setattr(redaction, "decrypt_pdf_in_place", qpdf)


def fail_rendering_until_repaired(monkeypatch):
    # Rendering redacted pages raises WandError until the returned fake
    # pdftocairo has repaired the file
    repaired = []

    def get_images(pdf_reader, filename, pages):
        for page in pages:
            yield page, f"page-{page}.png"

    def render(image_filename, instr, dpi):
        if not repaired:
            raise WandError("cannot render")
        return PdfReader(CROPBOX_PDF).pages[0]

    def repair(filename, password=None):
        repaired.append(filename)
        return filename

    monkeypatch.setattr(redaction, "get_images_from_pdf", get_images)
    monkeypatch.setattr(redaction, "get_redacted_page", render)
    return repair


def write_unreadable_once():
    # Fake Ghostscript that claims success but writes an unreadable file on
    # its first run (the original), and leaves later inputs unchanged
    runs = []

    def rewrite(filename, password=None):
        if not runs:
            Path(filename).write_bytes(b"this is not a PDF")
        runs.append(filename)
        return filename

    return rewrite


def write_without_page_count(path, password=None):
    writer = PdfWriter(clone_from=CROPBOX_PDF)
    del writer.root_object["/Pages"][NameObject("/Count")]
    if password is not None:
        writer.encrypt(password, algorithm="AES-256")
    writer.write(path)

    reader = PdfReader(path)
    if password is not None:
        reader.decrypt(password)
    assert "/Count" not in reader.root_object["/Pages"]
    return path


@pytest.fixture
def cropbox_pdf():
    return CROPBOX_PDF


@pytest.fixture
def encrypted_pdf(tmp_path):
    writer = PdfWriter(clone_from=CROPBOX_PDF)
    # Ghostscript can't decrypt pypdf's RC4 and AES-128 encryption
    writer.encrypt("secret", algorithm="AES-256")
    path = tmp_path / "encrypted.pdf"
    writer.write(path)
    return path


@pytest.fixture
def pdf_without_page_count(tmp_path):
    return write_without_page_count(tmp_path / "without-count.pdf")


@pytest.fixture
def encrypted_pdf_without_page_count(tmp_path):
    return write_without_page_count(
        tmp_path / "encrypted-without-count.pdf", password="secret"
    )


@pytest.fixture
def garbage_pdf(tmp_path):
    path = tmp_path / "garbage.pdf"
    path.write_bytes(b"this is not a PDF")
    return path


@pytest.mark.parametrize("pdf_path,num_pages", [(CROPBOX_PDF, 1), (ROTATED_PDF, 4)])
def test_redaction_keeps_page_count(pdf_path, num_pages):
    reader = redact(pdf_path, make_page_instructions(num_pages))

    assert len(reader.pages) == num_pages


def test_redaction_replaces_only_redacted_pages_with_images():
    reader = redact(ROTATED_PDF, make_page_instructions(4, redacted_pages=[1]))

    assert reader.pages[0].extract_text()
    assert not reader.pages[1].extract_text()
    assert reader.pages[2].extract_text()


def test_redaction_of_encrypted_pdf_with_password(encrypted_pdf):
    reader = redact(encrypted_pdf, make_page_instructions(1), password="secret")

    assert not reader.is_encrypted
    assert reader.pages[0].extract_text()


def test_redaction_of_unreadable_file_fails(garbage_pdf):
    with pytest.raises(Exception, match="PDF Rewrite Error"):
        redact(garbage_pdf, make_page_instructions(1))


@pytest.mark.parametrize(
    "pdf_fixture,password,tools",
    [
        pytest.param("cropbox_pdf", None, {}, id="original"),
        pytest.param("encrypted_pdf", "secret", {}, id="pypdf-decrypts"),
        pytest.param(
            "garbage_pdf",
            None,
            {"cairo": repair_with(CROPBOX_PDF)},
            id="pdftocairo-repair",
        ),
        # pypdf counts the pages of unencrypted files by walking the page tree
        pytest.param("pdf_without_page_count", None, {}, id="missing-page-count"),
        # For encrypted files pypdf reads /Count and raises KeyError
        pytest.param(
            "encrypted_pdf_without_page_count",
            "secret",
            {"cairo": repair_with(CROPBOX_PDF)},
            id="encrypted-missing-page-count",
        ),
    ],
)
def test_redaction_falls_back_when_ghostscript_fails(
    request, monkeypatch, pdf_fixture, password, tools
):
    pdf_path = request.getfixturevalue(pdf_fixture)
    fake_tools(monkeypatch, **tools)

    reader = redact(pdf_path, make_page_instructions(1), password=password)

    assert reader.pages[0].extract_text()


@pytest.mark.parametrize(
    "pdf_fixture,password,tools",
    [
        pytest.param(
            "garbage_pdf",
            None,
            {"gs": keep_unchanged, "cairo": keep_unchanged, "qpdf": keep_unchanged},
            id="unreadable-tools-change-nothing",
        ),
        pytest.param("encrypted_pdf", None, {}, id="encrypted-without-password"),
        pytest.param("encrypted_pdf", "wrong", {}, id="encrypted-wrong-password"),
    ],
)
def test_redaction_of_broken_file_fails(
    request, monkeypatch, pdf_fixture, password, tools
):
    pdf_path = request.getfixturevalue(pdf_fixture)
    fake_tools(monkeypatch, **tools)

    with pytest.raises(Exception, match="PDF .* Error"):
        redact(pdf_path, make_page_instructions(1), password=password)


def test_redaction_falls_back_when_ghostscript_output_is_unreadable(monkeypatch):
    # Ghostscript claims success, but its output can't be read.
    # Another tool (currently pdftocairo) provides a readable file.
    fake_tools(monkeypatch, gs=write_unreadable_once(), cairo=repair_with(CROPBOX_PDF))

    reader = redact(CROPBOX_PDF, make_page_instructions(1))

    assert len(reader.pages) == 1


def test_redaction_succeeds_when_pdftocairo_makes_pdf_renderable(monkeypatch):
    repair_rendering = fail_rendering_until_repaired(monkeypatch)
    # Ghostscript succeeds, so the PDF can be read and only rendering fails.
    # pdftocairo repairs the file, so rendering works afterwards.
    fake_tools(monkeypatch, gs=keep_unchanged, cairo=repair_rendering)

    reader = redact(CROPBOX_PDF, make_page_instructions(1, redacted_pages=[0]))

    assert len(reader.pages) == 1


def test_redaction_fails_when_pdftocairo_cannot_make_pdf_renderable(monkeypatch):
    fail_rendering_until_repaired(monkeypatch)
    # Ghostscript succeeds, so the PDF can be read and only rendering fails.
    # pdftocairo fails too, so no tool is left that could help.
    fake_tools(monkeypatch, gs=keep_unchanged, cairo=fail_rewrite)

    with pytest.raises(Exception, match="PDF .* Error"):
        redact(CROPBOX_PDF, make_page_instructions(1, redacted_pages=[0]))


@pytest.mark.parametrize(
    "pdf_path,num_pages,tools",
    [
        pytest.param(CROPBOX_PDF, 2, {}, id="too-many-instructions"),
        # Ghostscript claims success but returns fewer pages
        pytest.param(
            ROTATED_PDF,
            4,
            {"gs": repair_with(CROPBOX_PDF)},
            id="ghostscript-loses-pages",
        ),
    ],
)
def test_redaction_fails_on_page_count_mismatch(
    monkeypatch, pdf_path, num_pages, tools
):
    fake_tools(monkeypatch, **tools)

    with pytest.raises(AssertionError):
        redact(pdf_path, make_page_instructions(num_pages))
