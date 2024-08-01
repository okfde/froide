import logging
from types import ModuleType
from typing import Optional

from django.conf import settings
from django.template.loader import render_to_string

from froide.helper.text_utils import remove_closing_inclusive


def get_wp() -> Optional[ModuleType]:
    try:
        import weasyprint as _wp

        return _wp
    except ImportError:
        pass


logger = logging.getLogger(__name__)


class PDFGenerator(object):
    template_name: str

    def __init__(self, obj):
        self.obj = obj

    def get_pdf_bytes(self):
        wp = get_wp()
        if wp is None:
            return b""

        html = self.get_html_string()
        doc = wp.HTML(string=html)
        return doc.write_pdf()

    def get_html_string(self):
        ctx = self.get_context_data(self.obj)
        return render_to_string(self.template_name, ctx)

    def get_context_data(self, obj):
        return {"object": obj, "SITE_NAME": settings.SITE_NAME}


class FoiRequestPDFGenerator(PDFGenerator):
    template_name = "foirequest/pdf/foirequest.html"


class FoiRequestMessagePDFGenerator(PDFGenerator):
    template_name = "foirequest/pdf/foimessage.html"


class LetterPDFGenerator(PDFGenerator):
    template_name = "foirequest/pdf/message_letter.html"

    def get_publicbody(self):
        return self.obj.request.public_body

    def get_recipient_address(self):
        pb = self.get_publicbody()
        pb_address = ""
        if pb is not None:
            address = pb.address.splitlines()
            pb_address = [pb.name] + address
            pb_address = "\n".join(pb_address)
        return pb_address

    def get_context_data(self, obj):
        ctx = super().get_context_data(obj)

        ctx.update(
            {
                "recipient_address": self.get_recipient_address(),
                "text": self.get_letter_text(obj),
            }
        )
        return ctx

    def get_letter_text(self, message):
        text = message.plaintext.split(message.sender_email)[0]
        text = remove_closing_inclusive(text)
        return text
