import logging

from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.loader import render_to_string

try:
    import weasyprint as wp
    PDF_EXPORT_AVAILABLE = True

except ImportError:
    PDF_EXPORT_AVAILABLE = False

from froide.helper.text_utils import remove_closing_inclusive


logger = logging.getLogger(__name__)


class PDFGenerator(object):
    def __init__(self, obj):
        self.obj = obj

    def get_pdf_bytes(self):
        if not PDF_EXPORT_AVAILABLE:
            return b''
        return self.make_doc(self.obj)

    def make_doc(self, foirequest):
        ctx = self.get_context_data(foirequest)
        html = render_to_string(self.template_name, ctx)
        doc = wp.HTML(string=html)
        return doc.write_pdf()

    def get_context_data(self, obj):
        return {
            'object': obj,
            'SITE_NAME': settings.SITE_NAME
        }


class FoiRequestPDFGenerator(PDFGenerator):
    template_name = 'foirequest/pdf/foirequest.html'


class LetterPDFGenerator(PDFGenerator):
    template_name = 'foirequest/pdf/message_letter.html'

    def get_context_data(self, obj):
        ctx = super().get_context_data(obj)

        pb = obj.recipient_public_body
        pb_address = ''
        if pb is not None:
            address = pb.address.splitlines()
            pb_address = [pb.name] + address
            pb_address = '\n'.join(pb_address)

        ctx.update({
            'pb_address': pb_address,
            'text': self.get_letter_text(obj),
        })
        return ctx

    def get_letter_text(self, message):
        text = message.plaintext.split(message.sender_email)[0]
        text = remove_closing_inclusive(text)
        return text
