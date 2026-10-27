import base64
import io
import logging
import os
import shutil
import tempfile
import zlib

import PIL.Image as PILImage
from filingcabinet.pdf_utils import (
    decrypt_pdf_in_place,
    get_images_from_pdf,
    rewrite_hard_pdf_in_place,
    rewrite_pdf_in_place,
)
from pypdf import PasswordType, PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from wand.color import Color
from wand.drawing import Drawing
from wand.exceptions import DelegateError, WandError
from wand.image import Image

logger = logging.getLogger(__name__)


class PDFRedactionError(Exception):
    pass


class PDFCandidateError(Exception):
    # This candidate file can't be redacted, try the next one
    pass


def redact_file(pdf_file, instructions):
    try:
        # Limit to around a gigabyte for a 24 bit (3 bpp) image
        PILImage.MAX_IMAGE_PIXELS = int(1024 * 1024 * 1024 // 1 // 3)
        outpath = tempfile.mkdtemp()
        original = os.path.join(outpath, "original.pdf")
        with open(original, "wb") as f:
            f.write(pdf_file.read())
        output_file = try_redacting_file(original, outpath, instructions)
        with open(output_file, "rb") as f:
            return f.read()
    finally:
        shutil.rmtree(outpath)


def try_redacting_file(original, outpath, instructions):
    """
    Redact the first candidate file that can be read, has the expected
    number of pages and can be rendered.
    """
    password = instructions.get("password")
    check_password(original, password)

    for rewrite in (
        # Ghostscript
        rewrite_pdf_in_place,
        # the original as is (possibly encrypted with password)
        None,
        # qpdf, only rebuilds the structure
        decrypt_pdf_in_place,
        # pdftocairo, redraws every page, so it is the last resort
        rewrite_hard_pdf_in_place,
    ):
        candidate = make_candidate(original, outpath, rewrite, password)
        if candidate is None:
            continue

        try:
            pdf_reader = read_pdf(candidate, instructions)
            check_page_count(pdf_reader, instructions)
            return write_redacted_pdf(pdf_reader, candidate, outpath, instructions)
        except PDFCandidateError:
            logger.info("Redaction candidate failed", exc_info=True)
            continue

    raise PDFRedactionError("PDF Redaction Error")


def check_password(original, password):
    """
    No tool can get past a missing or wrong password, so stop before running
    any. Ghostscript would even exit successfully with a blank page.
    """
    try:
        pdf_reader = PdfReader(original, strict=False)
    except (PdfReadError, ValueError, OSError):
        # Leave broken files to the tools
        return

    if not pdf_reader.is_encrypted:
        return

    # Files with only an owner password open with an empty user password
    if pdf_reader.decrypt(password or "") == PasswordType.NOT_DECRYPTED:
        raise PDFRedactionError("PDF Password Error")


def make_candidate(original, outpath, rewrite, password):
    # Run the tool on a fresh copy, so every tool starts from the original
    if rewrite is None:
        return original
    candidate = os.path.join(outpath, "candidate.pdf")
    shutil.copyfile(original, candidate)
    return rewrite(candidate, password=password)


def read_pdf(pdf_path, instructions):
    try:
        pdf_reader = PdfReader(pdf_path, strict=False)
    except (PdfReadError, ValueError, OSError) as e:
        raise PDFCandidateError("Cannot read PDF") from e

    if pdf_reader.is_encrypted:
        pdf_reader.decrypt(instructions.get("password") or "")

    try:
        len(pdf_reader.pages)
    except (KeyError, PdfReadError) as e:  # KeyError: missing /Pages or /Count
        raise PDFCandidateError("Cannot count pages") from e

    return pdf_reader


def check_page_count(pdf_reader, instructions):
    num_pages = len(pdf_reader.pages)
    num_instructions = len(instructions.get("pages", []))
    if num_pages != num_instructions:
        raise PDFCandidateError(
            f"PDF has {num_pages} pages, expected {num_instructions}"
        )


def write_redacted_pdf(pdf_reader, pdf_path, outpath, instructions):
    dpi = 300
    load_invisible_font()
    output = PdfWriter()
    page_instructions = instructions.get("pages", [])

    page_image_numbers = [
        page_idx + 1
        for page_idx, instr in enumerate(page_instructions)
        if instr["rects"]
    ]
    image_generator = get_images_from_pdf(pdf_reader, pdf_path, page_image_numbers)

    def get_page_iterator(page_instructions, image_generator):
        for page_idx, instr in enumerate(page_instructions):
            if instr["rects"]:
                # filingcabinet runs pdftoppm and skips pages it fails on
                image_page, image_filename = next(image_generator, (None, None))
                if image_page != page_idx + 1:
                    raise PDFCandidateError(f"Cannot render page {page_idx + 1}")
                yield page_idx, instr, image_filename
            else:
                yield page_idx, instr, None

    page_iterator = get_page_iterator(page_instructions, image_generator)
    for page_idx, instr, image_filename in page_iterator:
        instr["width"] = float(instr["width"])
        try:
            if not image_filename:
                page = pdf_reader.pages[page_idx]
            else:
                page = get_redacted_page(image_filename, instr, dpi)
        except (WandError, DelegateError, ValueError) as e:
            raise PDFCandidateError(f"Cannot render page {page_idx + 1}") from e

        output.add_page(page)

    output_filename = os.path.join(outpath, "final.pdf")
    with open(output_filename, "wb") as f:
        output.write(f)
    return output_filename


def get_redacted_page(image_filename, instr, dpi):
    logger.debug("Redacting page %s", image_filename)
    writer = io.BytesIO()
    pdf = canvas.Canvas(writer)
    with Image(filename=image_filename, resolution=dpi) as image:
        image.background_color = Color("white")
        image.format = "jpg"
        image.alpha_channel = "remove"

        scale = image.width / instr["width"]

        with Drawing() as draw:
            for rect in instr["rects"]:
                rect = [r * scale for r in rect]
                draw.border_color = Color("black")
                draw.fill_color = Color("black")
                p = 2
                draw.rectangle(
                    left=rect[0] - p,
                    top=rect[1] - p,
                    width=rect[2] + p * 2,
                    height=rect[3] + p * 2,
                )

            draw(image)

        width = image.width * 72 / dpi
        height = image.height * 72 / dpi

        pdf.setPageSize((width, height))
        reportlab_io_img = ImageReader(io.BytesIO(image.make_blob()))
        pdf.drawImage(reportlab_io_img, 0, 0, width=width, height=height)

        for text_obj in instr["texts"]:
            add_text_on_pdf(pdf, text_obj, dpi, scale, height)

        pdf.showPage()
        pdf.save()

    writer.seek(0)
    temp_reader = PdfReader(writer)
    return temp_reader.pages[0]


def add_text_on_pdf(pdf, text_obj, dpi, scale, height):
    raw_text = text_obj["text"]
    if not raw_text:
        return
    font_name = "invisible"
    font_size = text_obj["fontSize"].replace("px", "")
    font_size = int(float(font_size) * 0.75)
    font_width = pdf.stringWidth(raw_text, font_name, font_size)
    if font_width <= 0:
        return
    box = text_obj["pos"]
    box = [b * scale * (72 / dpi) for b in box]
    box[1] = height - box[1] - box[3]

    text = pdf.beginText()
    text.setTextRenderMode(3)  # double invisible
    text.setFont(font_name, font_size)
    text.setTextOrigin(box[0], box[1])
    box_width = box[2]
    text.setHorizScale(100.0 * box_width / font_width)
    text.textLine(raw_text)
    pdf.drawText(text)


# Glyphless variation of vedaal's invisible font retrieved from
# http://www.angelfire.com/pr/pgpf/if.html, which says:
# 'Invisible font' is unrestricted freeware. Enjoy, Improve, Distribute freely
def load_invisible_font():
    font = """
eJzdlk1sG0UUx/+zs3btNEmrUKpCPxikSqRS4jpfFURUagmkEQQoiRXgAl07Y3vL2mvt2ml8APXG
hQPiUEGEVDhWVHyIC1REPSAhBOWA+BCgSoULUqsKcWhVBKjhzfPU+VCi3Flrdn7vzZv33ryZ3TUE
gC6chsTx8fHck1ONd98D0jnS7jn26GPjyMIleZhk9fT0wcHFl1/9GRDPkTxTqHg1dMkzJH9CbbTk
xbWlJfKEdB+Np0pBswi+nH/Nvay92VtfJp4nvEztUJkUHXsdksUOkveXK/X5FNuLD838ICx4dv4N
I1e8+ZqbxwCNP2jyqXoV/fmhy+WW/2SqFsb1pX68SfEpZ/TCrI3aHzcP//jitodvYmvL+6Xcr5mV
vb1ScCzRnPRPfz+LsRSWNasuwRrZlh1sx0E8AriddyzEDfE6EkglFhJDJO5u9fJbFJ0etEMB78D5
4Djm/7kjT0wqhSNURyS+u/2MGJKRu+0ExNkrt1pJti9p2x6b3TBJgmUXuzgnDmI8UWMbkVxeinCw
Mo311/l/v3rF7+01D+OkZYE0PrbsYAu+sSyxU0jLLtIiYzmBrFiwnCT9FcsdOOK8ZHbFleSn0znP
nDCnxbnAnGT9JeYtrP+FOcV8nTlNnsoc3bBAD85adtCNRcsSffjBsoseca/lBE7Q09LiJOm/ttyB
0+IqcwfncJt5q4krO5k7jV7uY+5m7mPebuLKUea7iHvk48w72OYF5rvZT8C8k/WvMN/Dc19j3s02
bzPvZZv3me9j/ox5P9t/xdzPzPVJcc7yGnPL/1+GO1lPVTXM+VNWOTRRg0YRHgrUK5yj1kvaEA1E
xAWiCtl4qJL2ADKkG6Q3XxYjzEcR0E9hCj5KtBd1xCxp6jV5mKP7LJBr1nTRK2h1TvU2w0akCmGl
5lWbBzJqMJsdyaijQaCm/FK5HqspHetoTtMsn4LO0T2mlqcwmlTVOT/28wGhCVKiNANKLiJRlxqB
F603axQznIzRhDSq6EWZ4UUs+xud0VHsh1U1kMlmNwu9kTuFaRqpURU0VS3PVmZ0iE7gct0MG/8+
2fmUvKlfRLYmisd1w8pk1LSu1XUlryM1MNTH9epTftWv+16gIh1oL9abJZyjrfF5a4qccp3oFAcz
Wxxx4DpvlaKKxuytRDzeth5rW4W8qBFesvEX8RFRmLBHoB+TpCmRVCCb1gFCruzHqhhW6+qUF6tC
pL26nlWN2K+W1LhRjxlVGKmRTFYVo7CiJug09E+GJb+QocMCPMWBK1wvEOfRFF2U0klK8CppqqvG
pylRc2Zn+XDQWZIL8iO5KC9S+1RekOex1uOyZGR/w/Hf1lhzqVfFsxE39B/ws7Rm3N3nDrhPuMfc
w3R/aE28KsfY2J+RPNp+j+KaOoCey4h+Dd48b9O5G0v2K7j0AM6s+5WQ/E0wVoK+pA6/3bup7bJf
CMGjwvxTsr74/f/F95m3TH9x8o0/TU//N+7/D/ScVcA=
""".encode("latin1")
    uncompressed = bytearray(zlib.decompress(base64.decodebytes(font)))
    ttf = io.BytesIO(uncompressed)
    ttf.name = "(invisible.ttf)"
    pdfmetrics.registerFont(TTFont("invisible", ttf))
