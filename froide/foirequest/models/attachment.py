from datetime import timedelta
from functools import partial

from django.conf import settings
from django.db import models, transaction
from django.dispatch import Signal
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from froide.document.models import Document
from froide.helper.storage import HashedFilenameStorage

from .message import FoiMessage

UNAPPROVE_TIMEFRAME = DELETE_TIMEFRAME = timedelta(hours=36)

PDF_FILETYPES = (
    "application/pdf",
    "application/x-pdf",
    "pdf/application",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
    "text/x-pdf",
)
MIMETYPE_OCTET_STREAM = "application/octet-stream"

WORD_FILETYPES = (
    "application/msword",
    "application/vnd.msword",
    "application/vnd.ms-word.document.macroenabled.12",
)

WORD_FILEEXTENSIONS = (
    ".doc",
    ".dot",
    ".wbk",
    ".docx",
    ".docm",
    "dotx",
    ".dotm",
    ".docb",
)

EXCEL_FILETYPES = (
    "application/msexcel",
    "application/vnd.ms-excel",
    "application/vnd.ms-excel.sheet.binary.macroenabled.12",
    "application/vnd.ms-excel.sheet.macroenabled.12",
)

EXCEL_FILEEXTENSIONS = (
    ".xlsx",
    ".xlsm",
    ".xlsb",
    ".xltx",
    ".xltm",
    ".xls",
    ".xlt",
    ".xls",
    ".xml",
    ".xml",
    ".xlam",
    ".xla",
    ".xlw",
    ".xlr",
)

ARCHIVE_FILETYPES = (
    "application/x-rar-compressed",
    "application/x-zip-compressed",
    "application/zip",
    "application/x-7z-compressed",
)

ARCHIVE_FILEEXTENSIONS = (
    ".rar",
    ".zip",
    ".7z",
)

POWERPOINT_FILETYPES = (
    "application/vnd.ms-powerpoint",
    "application/vnd.ms-powerpoint.presentation.macroenabled.12",
    "application/vnd.ms-powerpoint.slideshow.macroenabled.12",
)

POWERPOINT_FILETEXTENSIONS = (
    ".pptx",
    ".pptm",
    ".ppt",
    ".potx",
    ".potm",
    ".pot",
    ".ppsx",
    ".ppsm",
    ".pps",
)

IMAGE_FILETYPES = ("image/png", "image/jpeg", "image/jpg", "image/gif")

TEXT_FILETYPES = ("application/text-plain:formatted", "text/plain")

EMBEDDABLE_FILETYPES = PDF_FILETYPES + IMAGE_FILETYPES

POSTAL_CONTENT_TYPES = PDF_FILETYPES + IMAGE_FILETYPES


def upload_to(instance, filename):
    # name will be irrelevant
    # as hashed filename storage will drop it
    # and use only directory
    return "%s/%s" % (settings.FOI_MEDIA_PATH, instance.name)


class FoiAttachmentManager(models.Manager):
    def get_for_message(self, message, name):
        return (
            FoiAttachment.objects.filter(belongs_to=message, name=name, pending=False)
            .exclude(file="")
            .get()
        )


class FoiAttachment(models.Model):
    belongs_to = models.ForeignKey(
        FoiMessage,
        verbose_name=_("Belongs to message"),
        on_delete=models.CASCADE,
        related_name="foiattachment_set",
    )
    name = models.CharField(_("Name"), max_length=255)
    file = models.FileField(
        _("File"),
        upload_to=upload_to,
        max_length=255,
        storage=HashedFilenameStorage(),
        db_index=True,
    )
    size = models.IntegerField(_("Size"), blank=True, null=True)
    filetype = models.CharField(_("File type"), blank=True, max_length=100)
    format = models.CharField(_("Format"), blank=True, max_length=100)
    can_approve = models.BooleanField(_("User can approve"), default=True)
    approved = models.BooleanField(_("Approved"), default=False)
    approved_timestamp = models.DateTimeField(null=True, blank=True)
    redacted = models.ForeignKey(
        "self",
        verbose_name=_("Redacted Version"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="unredacted_set",
    )
    is_redacted = models.BooleanField(_("Is redacted"), default=False)
    converted = models.ForeignKey(
        "self",
        verbose_name=_("Converted Version"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="original_set",
    )
    is_converted = models.BooleanField(_("Is converted"), default=False)
    timestamp = models.DateTimeField(null=True, default=timezone.now)
    pending = models.BooleanField(default=False)
    is_moderated = models.BooleanField(_("Has been moderated"), default=False)

    document = models.OneToOneField(
        Document,
        null=True,
        blank=True,
        related_name="attachment",
        on_delete=models.SET_NULL,
    )

    objects = FoiAttachmentManager()

    attachment_available = Signal()
    attachment_approved = Signal()  # args: ['user', 'request', 'redacted']
    attachment_unapproved = Signal()  # args: ['user', 'request',]
    attachment_deleted = Signal()  # args: ['user', 'request',]
    attachment_redacted = Signal()  # args: ['user', 'request',]
    document_created = Signal()  # args: ['user', 'request']

    class Meta:
        ordering = ("name",)
        unique_together = (("belongs_to", "name"),)
        # order_with_respect_to = 'belongs_to'
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def __str__(self):
        return "%s (%s) of %s" % (self.name, self.size, self.belongs_to)

    @property
    def slug(self):
        # Introduce proper slug field later
        return self.name

    def index_content(self):
        return "\n".join((self.name,))

    def get_html_id(self):
        return _("attachment-%(id)d") % {"id": self.id}

    def get_bytes(self):
        self.file.open(mode="rb")
        try:
            return self.file.read()
        finally:
            self.file.close()

    @property
    def can_redact(self):
        return self.redacted_id is not None or (self.can_approve and self.is_pdf)

    @property
    def can_delete(self):
        if not self.belongs_to.is_postal:
            return False
        if not self.can_approve:
            return False
        now = timezone.now()
        return self.timestamp > (now - DELETE_TIMEFRAME)

    @property
    def can_unapprove(self):
        if not self.approved or not self.approved_timestamp:
            return False

        now = timezone.now()
        return self.approved_timestamp > (now - DELETE_TIMEFRAME)

    @property
    def can_change_approval(self):
        return self.can_unapprove if self.approved else self.can_approve

    @property
    def can_edit(self):
        return self.can_redact or self.can_delete or self.can_approve

    @property
    def can_link(self):
        return self.approved or not (self.can_redact and self.can_approve)

    @property
    def is_pdf(self):
        return self.filetype in PDF_FILETYPES or (
            self.name
            and self.name.endswith((".pdf", ".PDF"))
            and self.filetype == MIMETYPE_OCTET_STREAM
        )

    @classmethod
    def make_is_pdf_q(cls):
        return models.Q(filetype__in=PDF_FILETYPES) | (
            (models.Q(name__endswith=".pdf") | models.Q(name__endswith=".PDF"))
            & models.Q(filetype=MIMETYPE_OCTET_STREAM)
        )

    @property
    def is_word(self):
        return self.filetype in WORD_FILETYPES or (
            self.name and self.name.endswith(WORD_FILEEXTENSIONS)
        )

    @property
    def is_excel(self):
        return self.filetype in EXCEL_FILETYPES or (
            self.name and self.name.endswith(EXCEL_FILEEXTENSIONS)
        )

    @property
    def is_text(self):
        return self.filetype.startswith("text/")

    @property
    def is_archive(self):
        return self.filetype in ARCHIVE_FILETYPES or (
            self.name and self.name.endswith(ARCHIVE_FILEEXTENSIONS)
        )

    @property
    def is_powerpoint(self):
        return self.filetype in POWERPOINT_FILETYPES or (
            self.name and self.name.endswith(POWERPOINT_FILETEXTENSIONS)
        )

    @property
    def is_image(self):
        return (
            self.filetype.startswith("image/")
            or self.filetype in IMAGE_FILETYPES
            or self.name.endswith((".jpg", ".jpeg", ".gif", ".png"))
        )

    @property
    def is_mail_decoration(self):
        return self.is_image and self.size and self.size < 1024 * 60

    @property
    def is_irrelevant(self):
        return self.is_mail_decoration or self.is_signature

    @property
    def is_signature(self):
        return self.name.endswith((".p7s", ".vcf", ".asc")) and self.size < 1024 * 15

    @property
    def can_embed(self):
        return self.filetype in EMBEDDABLE_FILETYPES or self.is_pdf

    def get_anchor_url(self):
        if self.belongs_to:
            return self.belongs_to.get_absolute_url()
        return "#" + self.get_html_id()

    def get_domain_anchor_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_anchor_url())

    def get_absolute_url(self):
        fr = self.belongs_to.request
        return reverse(
            "foirequest-show_attachment",
            kwargs={
                "slug": fr.slug,
                "message_id": self.belongs_to.pk,
                "attachment_name": self.name,
            },
        )

    def get_file_url(self):
        """
        Hook method for django-filingcabinet
        """
        return self.get_absolute_domain_file_url()

    def get_file_path(self):
        return self.file.path

    def get_crossdomain_auth(self):
        from ..auth import AttachmentCrossDomainMediaAuth

        return AttachmentCrossDomainMediaAuth(
            {
                "object": self,
            }
        )

    def send_internal_file(self):
        return self.get_crossdomain_auth().send_internal_file()

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_absolute_domain_auth_url(self):
        return self.get_crossdomain_auth().get_full_auth_url()

    def get_authorized_absolute_domain_file_url(self):
        return self.get_absolute_domain_file_url(authorized=True)

    def get_absolute_domain_file_url(self, authorized=False):
        return self.get_crossdomain_auth().get_full_media_url(authorized=authorized)

    def approve_and_save(self, approve: bool = True) -> None:
        self.approved = approve
        self.approved_timestamp = timezone.now() if approve else None
        self.save()

        if self.document:
            foirequest = self.belongs_to.request
            should_be_public = foirequest.public and approve
            if self.document.public != should_be_public:
                self.document.public = should_be_public
                self.document.save()

    def remove_file_and_delete(self):
        if self.file:
            other_references = (
                FoiAttachment.objects.filter(file=self.file.name)
                .exclude(id=self.id)
                .exists()
            )
            if not other_references:
                self.file.delete(save=False)
        self.delete()

    def can_convert_to_pdf(self):
        from filingcabinet.pdf_utils import can_convert_to_pdf

        ft = self.filetype.lower()
        name = self.name.lower()
        return self.converted_id is None and can_convert_to_pdf(ft, name=name)

    def create_document(self, title=None):
        if self.document is not None:
            return self.document

        if not self.is_pdf:
            return
        if self.converted_id or self.redacted_id:
            return

        foirequest = self.belongs_to.request
        doc = Document.objects.create(
            original=self,
            user=foirequest.user,
            public=foirequest.public,
            title=title or self.name,
            foirequest=self.belongs_to.request,
            pending=True,
            publicbody=self.belongs_to.sender_public_body,
        )
        self.document = doc
        self.save()

        from filingcabinet.tasks import process_document_task

        transaction.on_commit(partial(process_document_task.delay, doc.pk))

        return doc
