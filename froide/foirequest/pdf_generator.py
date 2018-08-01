# -*- encoding: utf-8 -*-
import contextlib
import tempfile
import logging
import os
import shutil

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
    from pylatex.utils import escape_latex, italic

    PDF_EXPORT_AVAILABLE = True

except ImportError:
    PDF_EXPORT_AVAILABLE = False

from froide.helper.text_utils import (
    remove_closing_inclusive, remove_greeting_inclusive
)

logger = logging.getLogger(__name__)


class PDFGenerator(object):
    def __init__(self, obj):
        self.obj = obj

    def run(self, obj, filename):
        raise NotImplementedError

    @contextlib.contextmanager
    def get_pdf_filename(self):
        if not PDF_EXPORT_AVAILABLE:
            yield None
            return

        try:
            self.path = tempfile.mkdtemp()
            filename = os.path.join(self.path, 'output')

            doc = self.make_doc(self.obj)
            try:
                doc.generate_pdf(filename, clean=False, compiler="xelatex")
                doc.generate_pdf(filename, clean_tex=False, compiler="xelatex")
            except pylatex.errors.CompilerError as e:
                logger.exception(e)
                yield None
            else:
                yield filename + '.pdf'
        finally:
            shutil.rmtree(self.path)

    def get_pdf_bytes(self):
        if not PDF_EXPORT_AVAILABLE:
            return b''

        with self.get_pdf_filename() as filename:
            if filename is None:
                return b''
            with open(filename, 'rb') as f:
                return f.read()


class FoiRequestPDFGenerator(PDFGenerator):
    def make_doc(self, foirequest):
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
        doc.preamble.append(NoEscape("\\usepackage{helvet}"))
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

        return doc


def add_message_to_doc(doc, message):
    att_queryset = message.foiattachment_set.filter(
        is_redacted=False,
        is_converted=False
    )

    with doc.create(Description()) as descr:
        descr.add_item(str(_('From:')), message.real_sender)
        descr.add_item(str(_('To:')), message.get_text_recipient())
        descr.add_item(str(_('Date:')),
            formats.date_format(message.timestamp, "DATETIME_FORMAT"))
        descr.add_item(str(_('Via:')), message.get_kind_display())
        descr.add_item(str(_('URL:')), message.get_accessible_link())
        descr.add_item(str(_('Subject:')), message.subject)
        if len(att_queryset):
            itemize = Itemize()
            for att in att_queryset:
                itemize.add_item(att.name)
            descr.add_item(str(_('Attachments:')), itemize)

    doc.append(NoEscape('\\noindent\\makebox[\\linewidth]{\\rule{\\textwidth}{1pt}}'))
    doc.append(LineBreak())
    append_text(doc, message.plaintext)


def append_text(doc, text):
    lines = text.splitlines()
    line_broken = True
    with doc.create(FlushLeft()):
        for i, line in enumerate(lines):
            last = i == len(lines) - 1
            if not line_broken and not line.strip() and not last:
                doc.append(LineBreak())
                line_broken = True
                continue
            if not line.strip():
                continue
            doc.append(line + ('' if last else '\n'))
            line_broken = False


class LetterPDFGenerator(PDFGenerator):
    def make_doc(self, message):
        doc = Document(
            documentclass='scrlttr2',
            document_options=[
                'fontsize=11pt',
                'parskip=full',
                'paper=A4',
                'fromalign=right',
                'fromemail=true',
                'fromurl=true',
                'version=last'
            ],
            inputenc='utf8',
            fontenc=None,
            page_numbers=False,
            geometry_options=None,
            lmodern=None,
            textcomp=True,
        )
        doc.packages.append(Package('fontspec,xunicode'))
        doc.packages.append(Package('inputenc', 'utf8'))
        doc.packages.append(Package('eurosym'))
        doc.packages.append(Package('graphicx'))
        doc.packages.append(Package('babel', 'ngerman'))
        # doc.packages.append(Package('pdfpages'))
        doc.packages.append(Package('hyperref', 'hidelinks'))

        doc.append(NoEscape("\\lefthyphenmin=5"))
        doc.append(NoEscape('''
            \\newif\\ifquoteopen
                \\catcode`\\"=\\active
                \\DeclareRobustCommand*{"}{%
                \\ifquoteopen
                    \\quoteopenfalse \\grqq%
                \\else
                    \\quoteopentrue \\glqq%
                \\fi
        }'''))

        doc.append(NoEscape(
            '\\setkomavar{fromname}{%s}' % message.real_sender))

        user_address = message.sender_user.address
        if user_address:
            address = '\\\\'.join(
                escape_latex(x) for x in user_address.splitlines()
                if x.strip())
            doc.append(NoEscape(
                '\\setkomavar{fromaddress}{%s}' % address
            ))

        email = message.sender_email

        doc.append(NoEscape(
            '\\setkomavar{fromemail}{\\href{mailto:%(email)s}{%(email)s}}' % {
                'email': email
            }
        ))

        url = message.request.get_absolute_domain_short_url()
        doc.append(NoEscape(
            '\\setkomavar{fromurl}[]{\\href{%(url)s}{%(url)s}}' % {
                'url': url
            }
        ))

        doc.append(NoEscape('\\setkomavar{myref}[\\myrefname]{%s}' % (
            escape_latex('#' + str(message.request.pk))
        )))

        doc.append(NoEscape('\\setkomavar{customer}[%s]{%s}' % (
            escape_latex(_('Delivery')),
            escape_latex(_('Via fax and email')),
        )))

        doc.append(NoEscape('\\setkomavar{date}{\\today}'))
        doc.append(NoEscape(
            '\\setkomavar{subject}{%s}' % escape_latex(message.subject)
        ))

        pb = message.recipient_public_body
        if pb is not None:
            address = pb.address.splitlines()
            recipient_line = [pb.name] + address
            recipient_line = '\\\\'.join(
                escape_latex(x) for x in recipient_line
            )
            doc.append(NoEscape('''\\begin{letter}{%s}''' % recipient_line))

        doc.append(NoEscape('\\opening{%s}' % (
            escape_latex(_('Dear Ladies and Gentlemen,'))
        )))

        text = self.get_letter_text()
        append_text(doc, text)

        self.append_closing(doc)

        doc.append(NoEscape('\\end{letter}'))

        return doc

    def get_letter_text(self):
        message = self.obj
        text = message.plaintext.split(message.sender_email)[0]
        text = remove_greeting_inclusive(text)
        text = remove_closing_inclusive(text)
        return text

    def append_closing(self, doc):
        doc.append(NoEscape('\\closing{%s}' % (
            escape_latex(_('Kind Regards,'))
        )))
