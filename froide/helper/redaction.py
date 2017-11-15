import os
import base64
import tempfile
import io
import zlib

from PyPDF2 import PdfFileReader, PdfFileWriter

from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics

from wand.image import Image
from wand.drawing import Drawing
from wand.color import Color

from .document import PDF_FILETYPES


def can_redact_file(filetype, name=None):
    return filetype.lower() in PDF_FILETYPES or (
        name is not None and name.lower().endswith('.pdf')
    )


def redact_file(pdf_file, instructions):
    dpi = 150
    load_invisible_font()
    output = PdfFileWriter()
    pdf_reader = PdfFileReader(pdf_file, strict=False)
    num_pages = pdf_reader.getNumPages()
    assert num_pages == len(instructions)
    for pageNum, instr in enumerate(instructions):
        instr['width'] = float(instr['width'])
        if not instr['rects']:
            page = pdf_reader.getPage(pageNum)
        else:
            page = get_redacted_page(pdf_file, pageNum, instr, dpi)
        output.addPage(page)

    path = tempfile.mkdtemp()
    output_filename = os.path.join(path, 'final.pdf')
    with open(output_filename, 'wb') as f:
        output.write(f)
    return output_filename


def get_redacted_page(pdf_file, pageNum, instr, dpi):
    writer = io.BytesIO()
    pdf = canvas.Canvas(writer)
    filename = "{}[{}]".format(pdf_file.name, pageNum)
    with Image(filename=filename, resolution=dpi) as image:
        for rect in instr['rects']:
            width = image.width * 72 / dpi
            height = image.height * 72 / dpi
            scale = image.width / instr['width']
            rect = [r * scale for r in rect]

            with Drawing() as draw:
                draw.border_color = Color('black')
                draw.fill_color = Color('black')
                p = 2
                draw.rectangle(
                    left=rect[0] - p, top=rect[1] - p,
                    width=rect[2] + p * 2, height=rect[3] + p * 2)
                draw(image)

        pdf.setPageSize((width, height))
        image.format = 'jpg'
        image.alpha_channel = False
        reportlab_io_img = ImageReader(io.BytesIO(image.make_blob()))
        pdf.drawImage(reportlab_io_img, 0, 0, width=width, height=height)

        for text_obj in instr['texts']:
            add_text_on_pdf(pdf, text_obj, dpi, scale, height)

        pdf.showPage()
        pdf.save()

    writer.seek(0)
    temp_reader = PdfFileReader(writer)
    return temp_reader.getPage(0)


def add_text_on_pdf(pdf, text_obj, dpi, scale, height):
    raw_text = text_obj['text']
    if not raw_text:
        return
    font_name = 'invisible'
    font_size = text_obj['fontSize'].replace('px', '')
    font_size = int(float(font_size) * 0.75)
    font_width = pdf.stringWidth(raw_text, font_name, font_size)
    if font_width <= 0:
        return
    box = text_obj['pos']
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
""".encode('latin1')
    uncompressed = bytearray(zlib.decompress(base64.decodestring(font)))
    ttf = io.BytesIO(uncompressed)
    setattr(ttf, "name", "(invisible.ttf)")
    pdfmetrics.registerFont(TTFont('invisible', ttf))
