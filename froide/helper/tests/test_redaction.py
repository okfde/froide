import io
from pathlib import Path

import pytest
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import NameObject
from wand.exceptions import WandError

from froide.helper import redaction
from froide.helper.redaction import PDFRedactionError, redact_file

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


def skip_page_image_until_repaired(monkeypatch, failing_page):
    # Like filingcabinet, skip the image of the page pdftoppm fails on, until
    # the returned fake pdftocairo has repaired the file. Returns the image
    # filenames used for redacted pages, in order.
    repaired = []
    rendered = []

    def get_images(pdf_reader, filename, pages):
        for page in pages:
            if repaired or page != failing_page:
                yield page, f"page-{page}.png"

    def render(image_filename, instr, dpi):
        rendered.append(image_filename)
        return PageObject.create_blank_page(width=100, height=100)

    def repair(filename, password=None):
        repaired.append(filename)
        return filename

    monkeypatch.setattr(redaction, "get_images_from_pdf", get_images)
    monkeypatch.setattr(redaction, "get_redacted_page", render)
    return repair, rendered


def write_unreadable(filename, password=None):
    Path(filename).write_bytes(b"this is not a PDF")
    return filename


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
def owner_password_only_pdf(tmp_path):
    writer = PdfWriter(clone_from=CROPBOX_PDF)
    # Restricts permissions only, anyone can open it without a password
    writer.encrypt(user_password="", owner_password="owner", algorithm="AES-256")
    path = tmp_path / "owner-password-only.pdf"
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


@pytest.fixture
def duplicate_info_pdf(tmp_path):
    # A trailer whose first /Info points at the catalog makes Ghostscript
    # report "circular reference to indirect object"
    writer = PdfWriter(clone_from=ROTATED_PDF)
    buffer = io.BytesIO()
    writer.write(buffer)
    root = b"/Root %d 0 R" % writer.root_object.indirect_reference.idnum
    duplicate_info = root.replace(b"/Root", b"/Info")
    path = tmp_path / "duplicate-info.pdf"
    path.write_bytes(buffer.getvalue().replace(root, root + b" " + duplicate_info, 1))
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


def test_redaction_of_owner_password_only_pdf_without_password(
    owner_password_only_pdf,
):
    reader = redact(owner_password_only_pdf, make_page_instructions(1))

    assert not reader.is_encrypted
    assert reader.pages[0].extract_text()


def test_redaction_of_unreadable_file_fails(garbage_pdf):
    with pytest.raises(PDFRedactionError, match="PDF Redaction Error"):
        redact(garbage_pdf, make_page_instructions(1))


@pytest.mark.parametrize(
    "pdf_fixture,password,tools",
    [
        pytest.param("cropbox_pdf", None, {}, id="original"),
        pytest.param("encrypted_pdf", "secret", {}, id="pypdf-decrypts"),
        pytest.param(
            "garbage_pdf",
            None,
            {"qpdf": repair_with(CROPBOX_PDF)},
            id="qpdf-repair",
        ),
        # pypdf counts the pages of unencrypted files by walking the page tree
        pytest.param("pdf_without_page_count", None, {}, id="missing-page-count"),
        # For encrypted files pypdf reads /Count and raises KeyError
        pytest.param(
            "encrypted_pdf_without_page_count",
            "secret",
            {"qpdf": repair_with(CROPBOX_PDF)},
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


def test_redaction_fails_when_tools_change_nothing(monkeypatch, garbage_pdf):
    fake_tools(
        monkeypatch, gs=keep_unchanged, cairo=keep_unchanged, qpdf=keep_unchanged
    )

    with pytest.raises(PDFRedactionError, match="PDF Redaction Error"):
        redact(garbage_pdf, make_page_instructions(1))


@pytest.mark.parametrize(
    "password",
    [
        pytest.param(None, id="missing-password"),
        pytest.param("wrong", id="wrong-password"),
    ],
)
def test_redaction_of_encrypted_pdf_without_right_password_fails(
    encrypted_pdf, password
):
    # Real tools: no tool can get past a missing or wrong password, so give up
    # right away. Ghostscript would exit successfully with a blank page.
    with pytest.raises(PDFRedactionError, match="PDF Password Error"):
        redact(encrypted_pdf, make_page_instructions(1), password=password)


def test_redaction_falls_back_when_ghostscript_output_is_unreadable(monkeypatch):
    # Ghostscript claims success, but its output can't be read.
    # The original is still readable and gets redacted instead.
    fake_tools(monkeypatch, gs=write_unreadable)

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

    with pytest.raises(PDFRedactionError, match="PDF Redaction Error"):
        redact(CROPBOX_PDF, make_page_instructions(1, redacted_pages=[0]))


def test_redaction_succeeds_when_pdftocairo_makes_page_image_renderable(monkeypatch):
    repair, rendered = skip_page_image_until_repaired(monkeypatch, failing_page=1)
    # pdftoppm fails on page 1, so the image of page 2 must not be used for it.
    # pdftocairo repairs the file, so every page gets its own image afterwards.
    fake_tools(monkeypatch, gs=keep_unchanged, cairo=repair)

    redact(ROTATED_PDF, make_page_instructions(4, redacted_pages=[0, 1]))

    assert rendered == ["page-1.png", "page-2.png"]


def test_redaction_fails_when_pdftocairo_cannot_make_page_image_renderable(
    monkeypatch,
):
    _, rendered = skip_page_image_until_repaired(monkeypatch, failing_page=1)
    # pdftoppm fails on page 1 and pdftocairo fails too, so no tool is left
    # that could help
    fake_tools(monkeypatch, gs=keep_unchanged, cairo=fail_rewrite)

    with pytest.raises(PDFRedactionError, match="PDF Redaction Error"):
        redact(ROTATED_PDF, make_page_instructions(4, redacted_pages=[0, 1]))

    assert rendered == []


def test_redaction_falls_back_when_ghostscript_loses_pages(monkeypatch):
    # Ghostscript claims success but returns fewer pages.
    # The original has the right page count and gets redacted instead.
    fake_tools(monkeypatch, gs=repair_with(CROPBOX_PDF))

    reader = redact(ROTATED_PDF, make_page_instructions(4))

    assert len(reader.pages) == 4


def test_redaction_of_pdf_with_duplicate_info_keeps_all_pages(duplicate_info_pdf):
    # Real tools: Ghostscript 10.02 turns this file into a single blank page,
    # 10.08 keeps all pages. Either way all pages must end up redacted.
    reader = redact(duplicate_info_pdf, make_page_instructions(4))

    assert len(reader.pages) == 4


def test_redaction_fails_on_page_count_mismatch(monkeypatch):
    fake_tools(monkeypatch)

    with pytest.raises(PDFRedactionError, match="PDF Redaction Error"):
        redact(CROPBOX_PDF, make_page_instructions(2))
