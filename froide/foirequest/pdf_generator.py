import tempfile
import logging
import os

from django.utils.translation import ugettext_lazy as _
from django.utils import formats
from django.conf import settings

try:
    import pylatex
    from pylatex import (
        Document, Package, NoEscape, PageStyle, Head,
        Description, Foot, NewPage, LineBreak,
        FlushLeft, Itemize
    )
    from pylatex.utils import italic

    PDF_EXPORT_AVAILABLE = True

except ImportError:
    PDF_EXPORT_AVAILABLE = False


logger = logging.getLogger(__name__)


def get_foirequest_pdf_bytes(foirequest):
    if not PDF_EXPORT_AVAILABLE:
        return b''

    try:
        path = make_request_document(foirequest)
    except pylatex.errors.CompilerError as e:
        logger.warn(e)
        return b''

    with open(path, 'rb') as f:
        return f.read()


def make_request_document(foirequest):
    doc = Document(
        lmodern=True,
        geometry_options={
            "a4paper": True,
            "margin": "1in",
        },
    )
    # Change font
    doc.packages.append(Package('fontspec,xunicode,array'))
    doc.packages.append(Package('sectsty'))
    doc.preamble.append(NoEscape("\\setmainfont{Helvetica}"))
    doc.preamble.append(NoEscape("\\sectionfont{\\fontsize{12}{15}\\selectfont}"))

    # Adjust description list
    doc.packages.append(Package('enumitem'))
    doc.preamble.append(NoEscape("\\setlist[description]{labelindent=0cm,style=multiline,leftmargin=1.5cm}"))

    # Hyphenation
    doc.append(NoEscape("\\lefthyphenmin=5"))
    doc.append(NoEscape("\\sloppy"))

    # doc.preamble.append(Command('title', foirequest.title))
    # doc.preamble.append(Command('author', foirequest.get_absolute_domain_short_url()))
    # doc.preamble.append(Command('date', NoEscape('\\today')))
    # doc.append(NoEscape('\\maketitle'))

    # Set up header and footer
    header = PageStyle("header")
    with header.create(Foot("L")):
        header.append(italic(settings.SITE_NAME))
    with header.create(Head("C")):
        header.append(foirequest.title)
    with header.create(Foot("R")):
        header.append(str(
            _('Request #{request_no}').format(request_no=foirequest.pk)))
    with header.create(Foot("C")):
        header.append(italic(NoEscape(r'Seite \thepage\ von \pageref{LastPage}')))
    doc.preamble.append(header)
    doc.change_document_style("header")

    for i, message in enumerate(foirequest.messages):
        last = i == len(foirequest.messages) - 1
        add_message_to_doc(doc, message)
        if not last:
            doc.append(NewPage())

    path = tempfile.mkdtemp()
    dest = os.path.join(path, '%s' % foirequest.pk)
    doc.generate_pdf(dest, clean=False, compiler="xelatex")
    doc.generate_pdf(dest, clean_tex=False, compiler="xelatex")

    return dest + '.pdf'


def add_message_to_doc(doc, message):
    att_queryset = message.foiattachment_set.filter(
        is_redacted=False,
        is_converted=False
    )

    with doc.create(Description()) as descr:
        descr.add_item(str(_('From:')), message.real_sender)
        descr.add_item(str(_('To:')), message.get_text_recipient())
        if message.is_postal:
            descr.add_item(str(_('Date:')),
                formats.date_format(message.timestamp, "DATE_FORMAT"))
            descr.add_item(str(_('Via:')), str(_('Postal Mail')))
        else:
            descr.add_item(str(_('Date:')),
                formats.date_format(message.timestamp, "DATETIME_FORMAT"))
            descr.add_item(str(_('Via:')), str(_('Email')))
        descr.add_item(str(_('URL:')), message.get_accessible_link())
        descr.add_item(str(_('Subject:')), message.subject)
        if len(att_queryset):
            itemize = Itemize()
            for att in att_queryset:
                itemize.add_item(att.name)
            descr.add_item(str(_('Attachments:')), itemize)

    doc.append(NoEscape('\\noindent\\makebox[\\linewidth]{\\rule{\\textwidth}{1pt}}'))
    doc.append(LineBreak())

    lines = message.plaintext.splitlines()
    with doc.create(FlushLeft()):
        for i, line in enumerate(lines):
            last = i == len(lines) - 1
            if not line.strip() and not last:
                doc.append(LineBreak())
                continue
            doc.append(line + ('' if last else '\n'))
            # doc.append(LineBreak())
