import contextlib

from PyPDF2 import PdfFileReader
from PIL import Image as PILImage
import wand
from wand.image import Image
try:
    import tesserocr
except ImportError:
    tesserocr = None
try:
    import pdflib
except ImportError:
    pdflib = None


TESSERACT_LANGUAGE = {
    'en': 'eng',
    'de': 'deu'
}


class PDFProcessor(object):
    def __init__(self, filename, language=None, config=None):
        self.filename = filename
        self.pdf_reader = PdfFileReader(filename)
        self.num_pages = self.pdf_reader.getNumPages()
        self.language = language
        self.config = config or {}

    def get_meta(self):
        doc_info = self.pdf_reader.getDocumentInfo()
        return {
            'title': doc_info.title
        }

    def get_images(self, pages=None, resolution=300):
        if pages is None:
            pages = range(self.num_pages)
        for page_no in pages:
            with self.get_image(page_no, resolution=resolution) as img:
                yield img

    @contextlib.contextmanager
    def get_image(self, page_no, resolution=300):
        filename = "{}[{}]".format(self.filename, page_no)
        with Image(
                filename=filename,
                resolution=resolution,
                background=wand.color.Color('#fff')) as img:
            img.alpha_channel = False
            yield img

    def get_text(self, pages=None):
        if pages is None:
            pages = range(self.num_pages)
        pdflib_pages = None
        if pdflib is not None:
            pdflib_doc = pdflib.Document(self.filename)
            pdflib_pages = list(pdflib_doc)
        for page_no in pages:
            if pdflib_pages is not None:
                page = pdflib_pages[page_no]
                text = ' '.join(page.lines).strip()
            else:
                page = self.pdf_reader.getPage(page_no)
                text = page.extractText()
            if not text.strip():
                text = self.run_ocr(page_no)
            yield text.strip()

    def run_ocr(self, page_no):
        if tesserocr is None:
            return ''
        with self.get_image(page_no, resolution=300) as img:
            pil_image = PILImage.frombytes('RGB', img.size, img.make_blob('RGB'))
            return tesserocr.image_to_text(
                pil_image,
                lang=TESSERACT_LANGUAGE[self.language],
                path=self.config.get('TESSERACT_DATA_PATH', '')
            )

    def save_pages(self, path, **kwargs):
        for page, img in enumerate(self.get_images(**kwargs), 1):
            filename = path.format(page=page)
            img.save(filename=filename)
            yield filename


def crop_image(image_path, left, top, width, height):
    with Image(filename=image_path) as img:
        img.alpha_channel = False
        img.crop(left, top, left + width, top + height)
        return img.make_blob('gif')
