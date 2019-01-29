import io
import logging
import os
import shutil
import subprocess
import tempfile

from django.conf import settings

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from wand.image import Image
from wand.color import Color

from froide.document.pdf_utils import PDFProcessor


OFFICE_FILETYPES = (
    'application/msexcel',
    'application/vnd.ms-excel',
    'application/msword',
    'application/vnd.msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
)
OFFICE_EXTENSIONS = (
    '.doc',
    '.docx',
    '.odt'
)

PDF_FILETYPES = (
    'application/pdf',
    'application/x-pdf',
    'pdf/application',
    'application/acrobat',
    'applications/vnd.pdf',
    'text/pdf',
    'text/x-pdf'
)

IMAGE_FILETYPES = (
    'image/png',
    'image/jpeg',
    'image/jpg',
    'image/gif'
)

TEXT_FILETYPES = (
    'application/text-plain:formatted',
    'text/plain'
)

EMBEDDABLE_FILETYPES = (
    PDF_FILETYPES +
    IMAGE_FILETYPES
)

POSTAL_CONTENT_TYPES = PDF_FILETYPES + IMAGE_FILETYPES


def can_convert_to_pdf(filetype, name=None):
    return filetype.lower() in OFFICE_FILETYPES or (
        name is not None and name.lower().endswith(OFFICE_EXTENSIONS))


def convert_to_pdf(filepath, binary_name=None, construct_call=None, timeout=120):
    if binary_name is None and construct_call is None:
        return
    outpath = tempfile.mkdtemp()
    path, filename = os.path.split(filepath)
    name, extension = filename.rsplit('.', 1)
    output_file = os.path.join(outpath, '%s.pdf' % name)
    arguments = [
        binary_name,
        '--headless',
        '--nodefault',
        '--nofirststartwizard',
        '--nolockcheck',
        '--nologo',
        '--norestore',
        '--invisible',
        '--convert-to',
        'pdf',
        '--outdir',
        outpath,
        filepath
    ]
    if construct_call is not None:
        arguments, output_file = construct_call(filepath, outpath)

    try:
        output_bytes = shell_call(arguments, outpath, output_file, timeout=timeout)
        return output_bytes
    except Exception as err:
        logging.error("Error during Doc to PDF conversion: %s", err)
    finally:
        shutil.rmtree(outpath)
    return None


def convert_images_to_ocred_pdf(filenames, instructions=None):
    outpath = tempfile.mkdtemp()
    output_file = os.path.join(outpath, 'out.pdf')
    pdf_bytes = convert_images_to_pdf(filenames, instructions=instructions)
    with open(output_file, 'wb') as f:
        f.write(pdf_bytes)
    processor = PDFProcessor(
        output_file, language=settings.LANGUAGE_CODE
    )
    return processor.run_ocr(timeout=180)


def run_ocr(filename, language=None, binary_name='ocrmypdf', timeout=50):
    if binary_name is None:
        return
    outpath = tempfile.mkdtemp()
    output_file = os.path.join(outpath, 'out.pdf')
    arguments = [
        binary_name,
        '-l',
        language,
        '--deskew',
        # '--title', title
        filename,
        output_file
    ]
    try:
        output_bytes = shell_call(arguments, outpath, output_file, timeout=timeout)
        return output_bytes
    except Exception as err:
        logging.error("Error during PDF OCR: %s", err)
    finally:
        shutil.rmtree(outpath)
    return None


def shell_call(arguments, outpath, output_file, timeout=50):
    env = dict(os.environ)
    env.update({'HOME': outpath})

    logging.info("Running: %s", arguments)
    logging.info("Env: %s", env)
    out, err = '', ''
    p = None
    try:
        p = subprocess.Popen(
            arguments,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )

        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if p is not None:
            p.kill()
            out, err = p.communicate()
    finally:
        if p is not None and p.returncode is None:
            p.kill()
            out, err = p.communicate()
    if p is not None and p.returncode == 0:
        if os.path.exists(output_file):
            with open(output_file, 'rb') as f:
                return f.read()
    raise Exception(err)


def decrypt_pdf_in_place(filename, timeout=50):
    try:
        temp_dir = tempfile.mkdtemp()

        # I'm not sure if a qpdf failure could leave the file in a halfway
        # state, so have it write to a temporary file instead of reading from one
        temp_out = os.path.join(temp_dir, 'qpdf_out.pdf')

        arguments = ['qpdf', '--decrypt', filename, temp_out]
        output_bytes = shell_call(arguments, temp_dir, temp_out, timeout=timeout)

        # I'm not sure if a qpdf failure could leave the file in a halfway
        # state, so write to a temporary file and then use os.rename to
        # overwrite the original atomically.
        # (We use shutil.move instead of os.rename so it'll fall back to a copy
        #  operation if the dir= argument to mkdtemp() gets removed)
        with open(filename, 'wb') as f:
            f.write(output_bytes)
        return filename
    except Exception as err:
        logging.error("Error during PDF decryption %s", err)
        return None
    finally:
        # Delete all temporary files
        shutil.rmtree(temp_dir)


MAX_HEIGHT_A4 = 3507  # in pixels at 300 dpi


def convert_images_to_pdf(filenames, instructions=None, dpi=300):
    if instructions is None:
        instructions = [{} for _ in range(len(filenames))]
    a4_width, a4_height = A4
    writer = io.BytesIO()
    pdf = canvas.Canvas(writer, pagesize=A4)
    for filename, instruction in zip(filenames, instructions):
        with Image(filename=filename, resolution=dpi) as image:
            image.background_color = Color('white')
            image.format = 'jpg'
            image.alpha_channel = 'remove'
            try:
                degree = instruction.get('rotate', 0)
                if degree and degree % 90 == 0:
                    image.rotate(degree)
            except ValueError:
                pass

            if image.width > image.height:
                ratio = MAX_HEIGHT_A4 / image.width
            else:
                ratio = MAX_HEIGHT_A4 / image.height
            if ratio < 1:
                image.resize(round(ratio * image.width), round(ratio * image.height))

            width = image.width * 72 / dpi
            height = image.height * 72 / dpi
            pdf.setPageSize((width, height))
            reportlab_io_img = ImageReader(io.BytesIO(image.make_blob()))
            pdf.drawImage(reportlab_io_img, 0, 0, width=width, height=height)
            pdf.showPage()
    pdf.save()
    return writer.getvalue()
