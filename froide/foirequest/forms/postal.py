from functools import partial

from django import forms
from django.db import transaction
from django.forms.models import ModelChoiceField, ModelChoiceIterator
from django.utils.translation import gettext_lazy as _

from froide.account.services import AccountService
from froide.helper.form_utils import JSONMixin
from froide.helper.storage import make_unique_filename
from froide.helper.widgets import BootstrapRadioSelect
from froide.publicbody.models import PublicBody
from froide.publicbody.widgets import PublicBodySelect
from froide.upload.forms import FileUploaderField
from froide.upload.models import Upload

from ..models import FoiAttachment, FoiMessage, FoiRequest
from ..models.message import MessageKind
from ..tasks import move_upload_to_attachment
from ..validators import validate_postal_content_type
from .message import MessageEditMixin


class PostalUploadForm(MessageEditMixin, JSONMixin, forms.Form):
    sent = forms.TypedChoiceField(
        widget=BootstrapRadioSelect,
        choices=(
            (0, _("I have received the letter")),
            (1, _("I have sent the letter")),
        ),
        coerce=lambda x: bool(int(x)),
        required=True,
        initial=0,
        label=_("Did you receive or sent the letter?"),
        error_messages={"required": _("You have to decide!")},
    )

    publicbody = forms.ModelChoiceField(
        label=_("Public body"),
        queryset=PublicBody.objects.all(),
        required=True,
        widget=PublicBodySelect,
    )

    uploads = FileUploaderField(
        label=_("Upload scans or photos of the letter"),
        required=False,
        allowed_file_types=[".pdf", ".jpg", ".jpeg", ".png", ".gif"],
        help_text=_(
            "Uploaded scans can be PDF, JPG, PNG or GIF. They will be non-public "
            "by default and can be redacted after upload."
        ),
    )

    FIELD_ORDER = [
        "sent",
        "publicbody",
        "date",
        "registered_mail_date",
        "subject",
        "uploads",
        "text",
    ]

    def __init__(self, *args, **kwargs):
        self.foirequest = kwargs.pop("foirequest")
        self.user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        self.fields["publicbody"].initial = self.foirequest.public_body
        self.fields["publicbody"].widget.set_initial_object(self.foirequest.public_body)
        self.order_fields(self.FIELD_ORDER)
        self.account_service = AccountService(self.foirequest.user)

    def clean_uploads(self):
        upload_urls = self.cleaned_data["uploads"]
        uploads = []
        for upload_url in upload_urls:
            upload = Upload.objects.get_by_url(upload_url, user=self.user)
            if upload is None:
                raise forms.ValidationError(_("Bad URL"))
            validate_postal_content_type(upload.content_type)
            uploads.append(upload)
        return uploads

    def clean(self):
        cleaned_data = self.cleaned_data
        text = cleaned_data.get("text")
        uploads = cleaned_data.get("uploads")
        if not (text or uploads):
            raise forms.ValidationError(
                _(
                    "You need to provide either a letter summary or "
                    "a scan or photo of the letter."
                )
            )
        return cleaned_data

    def save(self):
        foirequest = self.foirequest
        message = FoiMessage(request=foirequest, kind=MessageKind.POST)
        # set subject, text, date via MessageEditMixin
        message = self.set_data_on_message(message)

        if self.cleaned_data["sent"]:
            message.is_response = False
            message.sender_user = message.request.user
            message.recipient_public_body = self.cleaned_data["publicbody"]
        else:
            message.is_response = True
            message.sender_public_body = self.cleaned_data["publicbody"]

        message.save()

        foirequest._messages = None
        foirequest.status = FoiRequest.STATUS.AWAITING_CLASSIFICATION
        foirequest.save()

        uploads = self.cleaned_data.get("uploads")
        if uploads:
            self.save_attachments(message, uploads)

        return message

    def save_attachments(self, message, uploads):
        self.names = set()
        for upload in uploads:
            self.create_attachment(message, upload)

    def create_attachment(self, message, upload):
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
            can_approve=True,
            approved=False,
            pending=True,
        )
        upload.ensure_saving()
        upload.save()

        transaction.on_commit(
            partial(move_upload_to_attachment.delay, att.id, upload.id)
        )
        return att


class ThinModelChoiceIterator(ModelChoiceIterator):
    def __init__(self, field):
        self.field = field
        # basically empty the queryset so the thousands of choices are not rendered into context
        self.queryset = field.queryset[:0]


class ThinModelChoiceField(ModelChoiceField):
    iterator = ThinModelChoiceIterator


class PostalEditForm(MessageEditMixin, JSONMixin, forms.Form):
    sent = forms.TypedChoiceField(
        choices=(
            (0, _("I have received the letter")),
            (1, _("I have sent the letter")),
        ),
        coerce=lambda x: bool(int(x)),
        required=True,
        initial=0,
        label=_("Did you receive or sent the letter?"),
        error_messages={"required": _("You have to decide!")},
    )

    publicbody = ThinModelChoiceField(
        label=_("Public body"),
        queryset=PublicBody.objects.all(),
        # queryset=PublicBody.objects.filter(id__gte=7600, id__lte=7700),
        required=True,
        # widget=PublicBodySelect,
    )

    def __init__(self, *args, **kwargs):
        self.message = kwargs.pop("message")  # XXX

        self.foirequest = kwargs.pop("foirequest")
        self.user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        self.fields["sent"].initial = 1 if self.message.sent else 0
        self.fields["publicbody"].initial = (
            self.message.sender_public_body or self.message.recipient_public_body
        )
        self.account_service = AccountService(self.foirequest.user)

    def save(self):
        foirequest = self.foirequest
        # set subject, text, date via MessageEditMixin
        message = self.set_data_on_message(self.message)

        if self.cleaned_data["sent"]:
            message.is_response = False
            message.sender_user = message.request.user
            message.recipient_public_body = self.cleaned_data["publicbody"]
        else:
            message.is_response = True
            message.sender_public_body = self.cleaned_data["publicbody"]

        message.save()

        foirequest._messages = None
        foirequest.status = FoiRequest.STATUS.AWAITING_CLASSIFICATION
        foirequest.save()

        # we don't need to handle/attach uploads, this has already been done

        return message
