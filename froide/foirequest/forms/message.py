import datetime
import logging
import re
from functools import partial
from typing import Optional

from django import forms
from django.conf import settings
from django.db import transaction
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from froide.account.forms import AddressBaseForm
from froide.account.services import AccountService
from froide.foirequest.models.event import FoiEvent
from froide.helper.fields import MultipleFileField
from froide.helper.storage import make_filename, make_unique_filename
from froide.helper.text_utils import apply_user_redaction, redact_subject
from froide.helper.widgets import (
    BootstrapCheckboxInput,
    BootstrapFileInput,
    BootstrapRadioSelect,
)
from froide.proof.forms import ProofAttachment
from froide.publicbody.models import PublicBody
from froide.publicbody.widgets import PublicBodySelect
from froide.upload.models import Upload

from ..models import FoiAttachment, FoiMessage, FoiRequest
from ..models.message import BULK_TAG, MessageKind
from ..tasks import convert_attachment_task, move_upload_to_attachment
from ..utils import (
    MailAttachmentSizeChecker,
    apply_minimum_redaction,
    construct_message_body,
    get_info_for_email,
    get_publicbody_for_email,
    possible_reply_addresses,
    redact_plaintext_with_request,
    select_foirequest_template,
)
from ..validators import (
    validate_no_placeholder,
    validate_postal_content_type,
    validate_upload_document,
)

publishing_denied = settings.FROIDE_CONFIG.get("publishing_denied", False)

ACCEPT_FILETYPES = "image/png,image/jpeg,image/gif,application/pdf"


class AttachmentSaverMixin(object):
    def clean_files(self):
        if "%s-files" % self.prefix not in self.files:
            return self.cleaned_data["files"]
        files = self.files.getlist("%s-files" % self.prefix)
        names = set()
        for file in files:
            validate_upload_document(file)
            name = make_filename(file.name)
            if name in names:
                raise forms.ValidationError(_("Upload files must have distinct names"))
            names.add(name)
        return self.cleaned_data["files"]

    def get_or_create_attachment(self, message, filename):
        try:
            att = FoiAttachment.objects.get(belongs_to=message, name=filename)
            return att, False
        except FoiAttachment.DoesNotExist:
            pass
        att = FoiAttachment(belongs_to=message, name=filename)
        return att, True

    def save_attachments(self, files, message, save_file=True):
        added = []

        attachment_names = {
            att.name for att in FoiAttachment.objects.filter(belongs_to=message)
        }

        for file in files:
            filename = make_unique_filename(file.name, attachment_names)
            attachment_names.add(filename)
            att = FoiAttachment(belongs_to=message, name=filename)
            att.size = file.size
            att.filetype = file.content_type
            if save_file:
                att.file.save(filename, file)
            else:
                att.pending = True
            att.can_approve = not message.request.not_publishable
            att.approved = False
            att.save()
            added.append(att)

            if save_file and att.can_convert_to_pdf():
                transaction.on_commit(partial(convert_attachment_task.delay, att.id))

        message._attachments = None

        return added


def get_default_initial_message(user):
    message = _("Dear Sir or Madam,\n\n…\n\nSincerely yours\n%(name)s\n")
    return message % {"name": user.get_full_name()}


def get_send_message_form(*args, **kwargs):
    foirequest = kwargs.pop("foirequest")
    last_message = list(foirequest.messages)[-1]
    # Translators: message reply prefix
    prefix = _("Re:")
    subject = last_message.subject
    if not subject.startswith(str(prefix)):
        subject = "{prefix} {subject}".format(
            prefix=prefix, subject=last_message.subject
        )
    if foirequest.is_overdue() and foirequest.awaits_response():
        days = (timezone.now() - foirequest.due_date).days + 1
        first_message = foirequest.messages[0]

        context = {
            "due": ngettext_lazy("%(count)s day", "%(count)s days", days)
            % {"count": days},
            "foirequest": foirequest,
            "first_message": first_message,
        }

        message = None

        if foirequest.law.overdue_reply:
            template_str = "{top}{body}{bottom}{footer}".format(
                top="{% autoescape off %}",
                body=foirequest.law.overdue_reply,
                bottom="{% endautoescape %}",
                footer='\r\n{% include "foirequest/emails/overdue_reply_footer.txt" %}',
            )
            message = Template(template_str).render(Context(context))
        if not message:
            message = render_to_string(
                select_foirequest_template(
                    foirequest, "foirequest/emails/overdue_reply.txt"
                ),
                context,
            )

    else:
        message = get_default_initial_message(foirequest.user)

    return SendMessageForm(
        *args,
        foirequest=foirequest,
        prefix="sendmessage",
        initial={"subject": subject, "message": message},
        **kwargs,
    )


def get_message_sender_form(*args, **kwargs):
    foimessage = kwargs.pop("foimessage")
    return MessagePublicBodySenderForm(*args, message=foimessage)


class MessagePublicBodySenderForm(forms.Form):
    sender = forms.ModelChoiceField(
        label=_("Sending Public Body"),
        queryset=PublicBody.objects.all(),
        widget=PublicBodySelect,
    )

    def __init__(self, *args, **kwargs):
        message = kwargs.pop("message", None)
        if "initial" not in kwargs:
            if message.sender_public_body:
                kwargs["initial"] = {"sender": message.sender_public_body}
        if "prefix" not in kwargs:
            kwargs["prefix"] = "message-sender-%d" % message.id
        self.message = message
        super().__init__(*args, **kwargs)
        self.fields["sender"].widget.set_initial_object(message.sender_public_body)

    def save(self):
        self.message.sender_public_body = self.cleaned_data["sender"]
        self.message.save()


def get_message_recipient_form(*args, **kwargs):
    foimessage = kwargs.pop("foimessage")
    return MessagePublicBodyRecipientForm(*args, message=foimessage)


class MessagePublicBodyRecipientForm(forms.Form):
    recipient = forms.ModelChoiceField(
        label=_("Recipient Public Body"),
        queryset=PublicBody.objects.all(),
        widget=PublicBodySelect,
    )

    def __init__(self, *args, **kwargs):
        message = kwargs.pop("message", None)
        if "initial" not in kwargs:
            if message.recipient_public_body:
                kwargs["initial"] = {"recipient": message.recipient_public_body}
        if "prefix" not in kwargs:
            kwargs["prefix"] = "message-recipient-%d" % message.id
        self.message = message
        super().__init__(*args, **kwargs)
        self.fields["recipient"].widget.set_initial_object(
            message.recipient_public_body
        )

    def save(self):
        self.message.recipient_public_body = self.cleaned_data["recipient"]
        self.message.save()


class SendMessageForm(AttachmentSaverMixin, AddressBaseForm, forms.Form):
    to = forms.ChoiceField(
        label=_("To"), choices=[], required=True, widget=BootstrapRadioSelect
    )
    subject = forms.CharField(
        label=_("Subject"),
        max_length=230,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        error_messages={
            "max_length": ngettext_lazy(
                "Ensure the subject has at most %(limit_value)d character (it has %(show_value)d).",
                "Ensure the subject has at most %(limit_value)d characters (it has %(show_value)d).",
                "limit_value",
            )
        },
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control"}),
        validators=[validate_no_placeholder],
        label=_("Your message"),
        help_text=_(
            "Don't include personal information. "
            "If you need to give your postal address "
            "enter it below."
        ),
    )

    files_help_text = _(
        "Uploaded scans can be PDF, JPG, PNG or GIF. They will be non-public "
        "by default and can be redacted after upload."
    )
    files = MultipleFileField(
        label=_("Other attachments"),
        required=False,
        validators=[validate_upload_document],
        help_text=files_help_text,
        widget=BootstrapFileInput(multiple=True, attrs={"accept": ACCEPT_FILETYPES}),
    )

    send_address = forms.BooleanField(
        label=_("Send physical address"),
        widget=BootstrapCheckboxInput,
        help_text=_(
            "If the public body is asking for your post "
            "address, check this and we will append the "
            "address below."
        ),
        required=False,
        initial=False,
    )

    field_order = ["to", "subject", "message", "files", "send_address"]

    def __init__(self, *args, **kwargs):
        self._store_params(kwargs)
        super().__init__(*args, **kwargs)
        self._initialize_fields()

    def _store_params(self, kwargs):
        self.foirequest = kwargs.pop("foirequest")

    def _initialize_fields(self):
        to_choices = possible_reply_addresses(self.foirequest)
        self.fields["to"].choices = to_choices
        if len(to_choices) == 1:
            self.fields["to"].initial = to_choices[0][0]

        address_optional = self.foirequest.law and self.foirequest.law.email_only

        self.fields["send_address"].initial = not address_optional
        self.fields["address"].initial = self.foirequest.user.address

    def get_user(self):
        return self.foirequest.user

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("send_address", False)
            and not cleaned_data.get("address", "").strip()
        ):
            raise forms.ValidationError(
                "You need to give a postal address, " "if you want to send it."
            )
        return cleaned_data

    def add_message_body(
        self,
        message,
        attachment_names=(),
        attachment_missing=(),
        proof: Optional[ProofAttachment] = None,
    ):
        message_body = self.cleaned_data["message"]
        send_address = self.cleaned_data.get("send_address", True)
        message.plaintext = construct_message_body(
            self.foirequest,
            message_body,
            send_address=send_address,
            attachment_names=attachment_names,
            attachment_missing=attachment_missing,
            proof=proof,
        )
        message.plaintext_redacted = redact_plaintext_with_request(
            message.plaintext, self.foirequest, redact_greeting=True
        )
        message.clear_render_cache()

    def make_message(self, foirequest: FoiRequest, recipient_email: str):
        user = self.get_user()

        address = self.cleaned_data.get("address", "")
        if address.strip() and address != user.address:
            user.address = address
            user.save()

        recipient_info = get_info_for_email(foirequest, recipient_email)
        recipient_name = recipient_info.name
        recipient_pb = recipient_info.publicbody
        if recipient_pb is None:
            recipient_pb = get_publicbody_for_email(recipient_email, self.foirequest)

        subject = re.sub(
            r"\s*\[#%s\]\s*$" % foirequest.pk, "", self.cleaned_data["subject"]
        )
        subject = "%s [#%s]" % (subject, foirequest.pk)
        user_replacements = user.get_redactions()
        subject_redacted = redact_subject(subject, user_replacements)

        message = FoiMessage(
            request=foirequest,
            subject=subject,
            kind=MessageKind.EMAIL,
            subject_redacted=subject_redacted,
            is_response=False,
            sender_user=user,
            sender_name=user.display_name(),
            sender_email=foirequest.secret_address,
            recipient_email=recipient_email.strip(),
            recipient_public_body=recipient_pb,
            recipient=recipient_name,
            timestamp=timezone.now(),
        )
        return message

    def save(self, user=None, bulk=False, proof: Optional[ProofAttachment] = None):
        recipient_email = self.cleaned_data["to"]
        message = self.make_message(self.foirequest, recipient_email)
        message.save()

        if bulk:
            message.tags.add(BULK_TAG)

        if self.cleaned_data.get("files"):
            self.save_attachments(self.files.getlist("%s-files" % self.prefix), message)

        message._attachments = None
        files = list(message.get_mime_attachments())

        if proof:
            # prepend to files list so it is definitely sent
            files = [proof.get_mime_attachment()] + files

        att_gen = MailAttachmentSizeChecker(files)
        attachments = list(att_gen)

        self.add_message_body(
            message,
            attachment_names=att_gen.send_files,
            attachment_missing=att_gen.non_send_files,
            proof=proof,
        )
        message.save()

        message.send(attachments=attachments)
        self.foirequest.message_sent.send(
            sender=self.foirequest, message=message, user=user
        )

        return message


def get_escalation_message_form(*args, **kwargs):
    foirequest = kwargs.pop("foirequest")
    template = kwargs.pop("template", "foirequest/emails/mediation_message.txt")

    subject = _("Complaint about request “{title}”").format(title=foirequest.title)

    return EscalationMessageForm(
        *args,
        foirequest=foirequest,
        initial={
            "subject": subject,
            "message": render_to_string(
                select_foirequest_template(foirequest, template),
                {
                    "law": foirequest.law.name,
                    "link": foirequest.get_auth_link(),
                    "name": foirequest.user.get_full_name(),
                },
            ),
        },
    )


class EscalationMessageForm(forms.Form):
    subject = forms.CharField(
        label=_("Subject"),
        max_length=230,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    message = forms.CharField(
        label=_("Your message"),
        widget=forms.Textarea(attrs={"class": "form-control"}),
        validators=[validate_no_placeholder],
    )

    def __init__(self, *args, **kwargs):
        foirequest = kwargs.pop("foirequest")
        super().__init__(*args, **kwargs)
        self.foirequest = foirequest

    def clean_message(self):
        message = self.cleaned_data["message"]
        message = message.replace("\r\n", "\n").strip()
        empty_form = get_escalation_message_form(foirequest=self.foirequest)
        if message == empty_form.initial["message"].strip():
            raise forms.ValidationError(
                _("You need to fill in the blanks in the template!")
            )
        return message

    def make_message(self, attachment_names=(), attachment_missing=()):
        user = self.foirequest.user
        subject = self.cleaned_data["subject"]
        subject = re.sub(r"\s*\[#%s\]\s*$" % self.foirequest.pk, "", subject)
        subject = "%s [#%s]" % (subject, self.foirequest.pk)

        user_replacements = user.get_redactions()
        subject_redacted = redact_subject(subject, user_replacements)

        plaintext = construct_message_body(
            self.foirequest,
            self.cleaned_data["message"],
            send_address=False,
            attachment_names=attachment_names,
            attachment_missing=attachment_missing,
        )

        plaintext_redacted = redact_plaintext_with_request(
            plaintext, self.foirequest, redact_greeting=True
        )

        return FoiMessage(
            request=self.foirequest,
            subject=subject,
            subject_redacted=subject_redacted,
            is_response=False,
            is_escalation=True,
            sender_user=self.foirequest.user,
            sender_name=self.foirequest.user.display_name(),
            sender_email=self.foirequest.secret_address,
            recipient_email=self.foirequest.law.mediator.email,
            recipient_public_body=self.foirequest.law.mediator,
            recipient=self.foirequest.law.mediator.name,
            timestamp=timezone.now(),
            plaintext=plaintext,
            plaintext_redacted=plaintext_redacted,
        )

    def save(self, user=None):
        from ..foi_mail import generate_foirequest_files

        file_generator = generate_foirequest_files(self.foirequest)
        att_gen = MailAttachmentSizeChecker(file_generator)
        attachments = list(att_gen)
        message = self.make_message(
            attachment_names=att_gen.send_files,
            attachment_missing=att_gen.non_send_files,
        )
        message.save()
        message.send(attachments=attachments)

        self.foirequest.message_sent.send(
            sender=self.foirequest, message=message, user=user
        )
        self.foirequest.escalated.send(
            sender=self.foirequest, message=message, user=user
        )
        return message


class MessageEditMixin(forms.Form):
    date = forms.DateField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("mm/dd/YYYY")}
        ),
        label=_("Send Date"),
        help_text=_("Please give the date the reply was sent."),
        localize=True,
    )
    registered_mail_date = forms.DateField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("mm/dd/YYYY")}
        ),
        label=_("Registered mail date"),
        required=False,
        help_text=_(
            "If this letter was registered on a different date than it was sent, enter it here"
        ),
        localize=True,
    )
    subject = forms.CharField(
        label=_("Subject"),
        required=False,
        max_length=230,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Subject")}
        ),
    )
    text = forms.CharField(
        label=_("Letter text summary"),
        widget=forms.Textarea(attrs={"rows": "4", "class": "form-control"}),
        required=False,
        help_text=_("Optionally give a summary of the letter contents"),
    )

    def clean_date(self):
        date = self.cleaned_data["date"]
        today = timezone.localdate()
        if date > today:
            raise forms.ValidationError(
                _("Your reply date is in the future, that is not possible.")
            )
        if date < self.foirequest.created_at.date():
            raise forms.ValidationError(
                _(
                    "Your reply date is before the request was made, "
                    "that is not possible."
                )
            )
        return date

    def set_data_on_message(self, message):
        # TODO: Check if timezone support is correct
        uploaded_date_midday = datetime.datetime.combine(
            self.cleaned_data["date"],
            datetime.time(12, 00, 00),
            tzinfo=timezone.get_current_timezone(),
        )

        # The problem we have when uploading postal messages is that they do not have a time, so we
        # need to invent one. 12am is a good assumption, however if we already have messages on this
        # date, we need to add it *after* all those messages
        # Example: User sends a foi request on 2011-01-01 at 3pm, the public body is fast and sends
        # out the reply letter on the same day. If we would assume 12am as the letter time, we would
        # place the postal reply earlier than the users message
        possible_message_timestamps = [
            msg.timestamp + datetime.timedelta(seconds=1)
            for msg in self.foirequest.messages
            if msg.timestamp.date() == self.cleaned_data["date"]
        ] + [uploaded_date_midday]

        message.timestamp = max(possible_message_timestamps)

        # If the last message on that date was sent out 1 sec before midnight, there is no good way
        # to place the postal reply, so just assume midday
        if message.timestamp.date() != self.cleaned_data["date"]:
            message.timestamp = uploaded_date_midday

        message.registered_mail_date = self.cleaned_data.get(
            "registered_mail_date", None
        )
        message.subject = self.cleaned_data.get("subject", "")
        user_replacements = self.foirequest.user.get_redactions()
        subject_redacted = redact_subject(message.subject, user_replacements)
        message.subject_redacted = subject_redacted
        message.plaintext = ""
        if self.cleaned_data.get("text"):
            message.plaintext = self.cleaned_data.get("text")
        message.plaintext_redacted = None
        message.plaintext_redacted = message.get_content()
        message.clear_render_cache()
        return message


class EditMessageForm(MessageEditMixin):
    def __init__(self, *args, **kwargs):
        self.message = kwargs.pop("message")
        self.foirequest = self.message.request
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = self.message.timestamp.date()
        self.fields["subject"].initial = self.message.subject
        self.fields["text"].initial = self.message.plaintext

    def save(self):
        message = self.set_data_on_message(self.message)
        message.save()


class PostalBaseForm(MessageEditMixin, AttachmentSaverMixin, forms.Form):
    scan_help_text = _("Uploaded scans can be PDF, JPG, PNG or GIF.")
    publicbody = forms.ModelChoiceField(
        label=_("Public body"),
        queryset=PublicBody.objects.all(),
        widget=PublicBodySelect,
    )

    files = MultipleFileField(
        label=_("Scanned Letter"),
        required=False,
        validators=[validate_upload_document],
        help_text=scan_help_text,
        widget=BootstrapFileInput(multiple=True, attrs={"accept": ACCEPT_FILETYPES}),
    )
    FIELD_ORDER = ["publicbody", "date", "subject", "text", "files"]

    def __init__(self, *args, **kwargs):
        self.foirequest = kwargs.pop("foirequest")
        super().__init__(*args, **kwargs)
        self.fields["publicbody"].label = self.PUBLICBODY_LABEL
        self.fields["publicbody"].initial = self.foirequest.public_body
        self.fields["publicbody"].widget.set_initial_object(self.foirequest.public_body)
        self.order_fields(self.FIELD_ORDER)

    def clean(self):
        cleaned_data = self.cleaned_data
        text = cleaned_data.get("text")
        if "%s-files" % self.prefix in self.files:
            files = self.files.getlist("%s-files" % self.prefix)
        else:
            files = None
        if not (text or files):
            raise forms.ValidationError(
                _(
                    "You need to provide either the letter text or "
                    "a scanned document."
                )
            )
        return cleaned_data

    def save(self):
        foirequest = self.foirequest
        message = FoiMessage(request=foirequest, kind=MessageKind.POST)
        message = self.set_data_on_message(message)
        message = self.contribute_to_message(message)
        message.save()

        foirequest._messages = None
        foirequest.status = FoiRequest.STATUS.AWAITING_CLASSIFICATION
        foirequest.save()

        if self.cleaned_data.get("files"):
            self.save_attachments(self.files.getlist("%s-files" % self.prefix), message)

        return message


def get_postal_reply_form(*args, **kwargs):
    foirequest = kwargs.pop("foirequest")
    return PostalReplyForm(
        *args, prefix="postal_reply", foirequest=foirequest, **kwargs
    )


class PostalReplyForm(PostalBaseForm):
    FIELD_ORDER = [
        "publicbody",
        "sender",
        "date",
        "subject",
        "text",
        "files",
        "not_publishable",
    ]
    PUBLICBODY_LABEL = _("Sender public body")

    sender = forms.CharField(
        label=_("Sender name"),
        required=False,
        max_length=250,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Sender Name")}
        ),
    )

    if publishing_denied:
        not_publishable = forms.BooleanField(
            label=_("You are not allowed to " "publish some received documents"),
            initial=False,
            required=False,
            help_text=_(
                "If the reply explicitly states that you are not allowed "
                "to publish some of the documents (e.g. due to copyright), "
                "check this."
            ),
        )

    def contribute_to_message(self, message):
        message.is_response = True
        message.sender_public_body = self.cleaned_data["publicbody"]
        if self.cleaned_data.get("sender"):
            message.sender_name = self.cleaned_data["sender"]
        message.not_publishable = self.cleaned_data.get("not_publishable", False)
        return message

    def save(self, user):
        message = super().save()
        FoiRequest.message_received.send(
            sender=self.foirequest, message=message, user=user
        )
        return message


def get_postal_message_form(*args, **kwargs):
    foirequest = kwargs.pop("foirequest")
    return PostalMessageForm(
        *args, prefix="postal_message", foirequest=foirequest, **kwargs
    )


class PostalMessageForm(PostalBaseForm):
    FIELD_ORDER = ["publicbody", "recipient", "date", "subject", "text", "files"]
    PUBLICBODY_LABEL = _("Receiving public body")

    recipient = forms.CharField(
        label=_("Recipient Name"),
        max_length=250,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Recipient Name")}
        ),
        required=False,
    )

    def contribute_to_message(self, message):
        message.is_response = False
        message.sender_user = message.request.user
        message.recipient_public_body = self.cleaned_data["publicbody"]
        if self.cleaned_data.get("recipient"):
            message.recipient = self.cleaned_data["recipient"]
        return message

    def save(self, user):
        message = super().save()
        FoiRequest.message_sent.send(sender=self.foirequest, message=message, user=user)
        return message


def get_postal_attachment_form(*args, **kwargs):
    foimessage = kwargs.pop("foimessage")
    prefix = "postal-attachment-%s" % foimessage.pk
    return PostalAttachmentForm(*args, prefix=prefix)


class PostalAttachmentForm(AttachmentSaverMixin, forms.Form):
    files = MultipleFileField(
        label=_("Scanned Document"),
        help_text=PostalBaseForm.scan_help_text,
        validators=[validate_upload_document],
        widget=BootstrapFileInput(multiple=True),
    )

    def save(self, message):
        files = self.files.getlist("%s-files" % self.prefix)
        result = self.save_attachments(files, message)
        return result


class TransferUploadForm(AttachmentSaverMixin, forms.Form):
    upload = forms.CharField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.foimessage = kwargs.pop("foimessage")
        super().__init__(*args, **kwargs)

    def clean_upload(self):
        upload_url = self.cleaned_data["upload"]
        upload = Upload.objects.get_by_url(upload_url, user=self.user)
        if upload is None:
            raise forms.ValidationError(_("Bad URL"))
        if upload.content_type not in self.foimessage.get_extra_content_types():
            validate_postal_content_type(upload.content_type)
        return upload

    def save(self, request):
        upload = self.cleaned_data["upload"]

        result = self.save_attachments([upload], self.foimessage, save_file=False)
        upload.ensure_saving()
        upload.save()

        att = result[0]

        transaction.on_commit(
            partial(move_upload_to_attachment.delay, att.id, upload.id)
        )

        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.ATTACHMENT_UPLOADED,
            self.foimessage.request,
            message=self.foimessage,
            user=request.user,
            **{"added": str(result)},
        )

        return result


class RedactMessageForm(forms.Form):
    subject = forms.CharField(required=False)
    content = forms.CharField(required=False)
    subject_length = forms.IntegerField(required=False)
    content_length = forms.IntegerField(required=False)

    def clean_field(self, field):
        val = self.cleaned_data[field]
        if not val:
            return []
        try:
            val = [int(x) for x in val.split(",")]
        except ValueError:
            raise forms.ValidationError("Bad value") from None
        return val

    def clean_subject(self):
        return self.clean_field("subject")

    def clean_content(self):
        return self.clean_field("content")

    def clean(self):
        if self.cleaned_data.get("content"):
            if not self.cleaned_data.get("content_length"):
                raise forms.ValidationError
        if self.cleaned_data.get("subject"):
            if not self.cleaned_data.get("subject_length"):
                raise forms.ValidationError

    def save(self, message):
        try:
            redacted_subject = apply_user_redaction(
                message.subject,
                self.cleaned_data["subject"],
                self.cleaned_data["subject_length"],
            )
            message.subject_redacted = redacted_subject
        except IndexError as e:
            logging.warning(e)

        try:
            redacted_content = apply_user_redaction(
                message.plaintext,
                self.cleaned_data["content"],
                self.cleaned_data["content_length"],
            )
            redacted_content = apply_minimum_redaction(
                message.request, redacted_content
            )
            message.plaintext_redacted = redacted_content
        except IndexError as e:
            logging.warning(e)

        message.clear_render_cache()
        message.save()


class PublicBodyUploader:
    def __init__(self, foirequest, token):
        self.foirequest = foirequest
        self.token = token
        self.account_service = AccountService(foirequest.user)

    def create_upload_message(self, upload_list):
        message = FoiMessage.objects.create(
            request=self.foirequest,
            timestamp=timezone.now(),
            is_response=True,
            plaintext="",
            plaintext_redacted="",
            html="",
            kind=MessageKind.UPLOAD,
            sender_public_body=self.foirequest.public_body,
        )
        self.foirequest.message_received.send(sender=self.foirequest, message=message)
        self.names = set()
        att_count = 0
        for upload_url in upload_list:
            att = self.create_attachment(message, upload_url)
            if att:
                att_count += 1

        return att_count

    def create_attachment(self, message, upload_url):
        upload = Upload.objects.get_by_url(upload_url, token=self.token)
        if upload is None:
            return

        name = self.account_service.apply_name_redaction(
            upload.filename, str(_("NAME"))
        )

        name = make_unique_filename(name, self.names)
        self.names.add(name)
        att = FoiAttachment.objects.create(
            belongs_to=message,
            name=name,
            size=upload.size,
            filetype=upload.content_type,
            can_approve=not message.request.not_publishable,
            approved=False,
            pending=True,
        )
        upload.ensure_saving()
        upload.save()

        transaction.on_commit(
            partial(move_upload_to_attachment.delay, att.id, upload.id)
        )
        return att
