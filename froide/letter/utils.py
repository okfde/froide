from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.datastructures import MultiValueDict
from django.utils import timezone
from django.utils.html import format_html
from django.utils import formats
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from froide.foirequest.forms import (
    get_send_message_form, get_postal_message_form
)
from froide.foirequest.models import FoiAttachment
from froide.foirequest.pdf_generator import (
    LetterPDFGenerator as BaseLetterPDFGenerator
)


class LetterPDFGenerator(BaseLetterPDFGenerator):
    template_name = 'letter/pdf/default.html'

    def __init__(self, obj, template=None, extra_context=None):
        self.obj = obj
        self.template = template
        self.extra_context = extra_context

    def get_context_data(self, obj):
        ctx = super().get_context_data(obj)
        ctx['subject'] = self.template.get_subject(self.extra_context)
        if self.extra_context:
            ctx.update(self.extra_context)
        return ctx

    def get_letter_text(self, message):
        return self.template.get_body(self.extra_context)


def get_example_context(letter_template, user, message):
    fields = letter_template.get_fields()
    context = {
        f['slug']: format_html('<mark>{}</mark>', f['label'])
        for f in fields
    }
    context.update({
        'address': format_html('<mark>{}\n{}</mark>',
            user.get_full_name(),
            user.address
        ),
        'user': user,
        'today': timezone.now(),
        'preview': True,
        'message': message,
        'foirequest': message.request
    })
    return context


def get_letter_generator(letter_template, message, context):
    return LetterPDFGenerator(
        message, template=letter_template,
        extra_context=context
    )


class MessageSender:
    def __init__(self, letter_template, message, form_data):
        self.letter_template = letter_template
        self.message = message
        self.foirequest = message.request
        self.form_data = form_data

    def send(self):

        if self.letter_template.email_subject:
            sent_message = self.send_email_message_form()
        else:
            sent_message = self.send_postal_message_form()

        if self.letter_template.tag:
            sent_message.tags.add(self.letter_template.tag)

        attachment = sent_message.attachments[0]
        pdf_bytes = self.generate_letter(extra_context={'redacted': True})
        att = self.add_attachment(sent_message, pdf_bytes)

        # Connect attachment
        attachment.redacted = att
        attachment.can_approve = False
        attachment.approved = False
        attachment.save()

        self.foirequest.status = 'awaiting_response'
        self.foirequest.save()

        return sent_message

    def get_context(self):
        context = {
            'today': timezone.now(),
            'foirequest': self.foirequest,
            'user': self.foirequest.user,
            'message': self.message,
        }
        context.update(self.form_data)
        return context

    def generate_letter(self, extra_context=None):
        context = self.get_context()
        context.update(self.form_data)
        if extra_context:
            context.update(extra_context)

        letter_generator = get_letter_generator(
            self.letter_template, self.message, context
        )
        return letter_generator.get_pdf_bytes()

    def get_uploaded_file(self, pdf_bytes, subject):
        return InMemoryUploadedFile(
            file=BytesIO(pdf_bytes),
            field_name='files',
            name='{}.pdf'.format(
                slugify(subject)[:25]
            ),
            content_type='application/pdf',
            size=len(pdf_bytes),
            charset=None,
            content_type_extra=None
        )

    def send_email_message_form(self):
        context = self.get_context()
        subject = self.letter_template.get_email_subject(context)
        pdf_bytes = self.generate_letter()
        letter = self.get_uploaded_file(pdf_bytes, subject)
        message_form = get_send_message_form(
            data={
                'sendmessage-to': self.foirequest.public_body.email,
                'sendmessage-subject': subject,
                'sendmessage-message': self.letter_template.get_email_body(context),
                'sendmessage-address': self.foirequest.user.address
            },
            files=MultiValueDict({
                'sendmessage-files': [letter]
            }),
            foirequest=self.foirequest,
            message_ready=True,
        )
        message_form.is_valid()
        sent_message = message_form.save()
        return sent_message

    def send_postal_message_form(self):
        context = self.get_context()
        subject = self.letter_template.get_subject(context)
        pdf_bytes = self.generate_letter()
        letter = self.get_uploaded_file(pdf_bytes, subject)
        date_str = formats.date_format(
            timezone.now(), "SHORT_DATE_FORMAT"
        )
        message_form = get_postal_message_form(
            data={
                'postal_message-publicbody': self.foirequest.public_body.id,
                'postal_message-recipient': '',
                'postal_message-date': date_str,
                'postal_message-subject': subject,
                'postal_message-text': self.letter_template.get_body(context),
            },
            files=MultiValueDict({
                'postal_message-files': [letter]
            }),
            foirequest=self.foirequest,
        )
        message_form.is_valid()
        sent_message = message_form.save()

        return sent_message

    def add_attachment(self, sent_message, pdf_bytes):
        att = FoiAttachment(
            belongs_to=sent_message,
            name='{}_{}.pdf'.format(
                slugify(sent_message.subject)[:25],
                _('redacted')
            ),
            is_redacted=True,
            filetype='application/pdf',
            approved=True,
            can_approve=True
        )
        pdf_file = ContentFile(pdf_bytes)
        att.size = pdf_file.size
        att.file.save(att.name, pdf_file)
        att.approve_and_save()
        return att
