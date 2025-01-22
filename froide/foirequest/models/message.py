import calendar
from email.utils import formatdate
from typing import List, Tuple

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.utils import formats, timezone
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase

from froide.helper.email_utils import make_address
from froide.helper.text_diff import CONTENT_CACHE_THRESHOLD, get_differences
from froide.helper.text_utils import quote_text, redact_plaintext, redact_subject
from froide.publicbody.models import PublicBody

from .request import FoiRequest, get_absolute_domain_short_url, get_absolute_short_url

BOUNCE_TAG = "bounce"
HAS_BOUNCED_TAG = "bounced"
AUTO_REPLY_TAG = "auto-reply"
BOUNCE_RESENT_TAG = "bounce-resent"
BULK_TAG = "bulk"


class FoiMessageManager(models.Manager):
    def get_throttle_filter(self, queryset, user, extra_filters=None):
        qs = queryset.filter(
            sender_user=user, is_response=False, kind=MessageKind.EMAIL
        )
        if extra_filters is not None:
            qs = qs.filter(**extra_filters)
        return qs, "timestamp"


class FoiMessageNoDraftsManager(FoiMessageManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_draft=False)


class MessageTag(TagBase):
    class Meta:
        verbose_name = _("message tag")
        verbose_name_plural = _("message tags")


class TaggedMessage(TaggedItemBase):
    tag = models.ForeignKey(
        MessageTag, on_delete=models.CASCADE, related_name="tagged_messages"
    )
    content_object = models.ForeignKey("FoiMessage", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("tagged message")
        verbose_name_plural = _("tagged messages")


class MessageKind(models.TextChoices):
    EMAIL = ("email", _("email"))
    POST = ("post", _("postal mail"))
    FAX = ("fax", _("fax"))
    UPLOAD = ("upload", _("upload"))
    PHONE = ("phone", _("phone call"))
    VISIT = ("visit", _("visit in person"))
    IMPORT = ("import", _("automatically imported"))


MESSAGE_KIND_ICONS = {
    MessageKind.EMAIL: "mail",
    MessageKind.POST: "newspaper-o",
    MessageKind.FAX: "fax",
    # it's received, so the download icon seems more appropriate
    MessageKind.UPLOAD: "download",
    MessageKind.PHONE: "phone",
    MessageKind.VISIT: "handshake-o",
    MessageKind.IMPORT: "cloud-download",
}

MANUAL_MESSAGE_KINDS = {MessageKind.POST, MessageKind.PHONE, MessageKind.VISIT}
MESSAGE_ID_PREFIX = "foimsg."


class FoiMessage(models.Model):
    request = models.ForeignKey(
        FoiRequest,
        verbose_name=_("Freedom of Information Request"),
        on_delete=models.CASCADE,
    )
    is_draft = models.BooleanField(_("is message a draft?"), default=False)
    sent = models.BooleanField(_("has message been sent?"), default=True)
    is_response = models.BooleanField(_("response?"), default=True)
    kind = models.CharField(
        max_length=10, choices=MessageKind.choices, default=MessageKind.EMAIL
    )
    is_escalation = models.BooleanField(_("Escalation?"), default=False)
    content_hidden = models.BooleanField(_("Content hidden?"), default=False)
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("From User"),
    )
    sender_email = models.CharField(_("From Email"), blank=True, max_length=255)
    sender_name = models.CharField(_("From Name"), blank=True, max_length=255)
    sender_public_body = models.ForeignKey(
        PublicBody,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("From Public Body"),
        related_name="send_messages",
    )

    recipient = models.CharField(_("Recipient"), max_length=255, blank=True, null=True)
    recipient_email = models.CharField(
        _("Recipient Email"), max_length=255, blank=True, null=True
    )
    recipient_public_body = models.ForeignKey(
        PublicBody,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Public Body Recipient"),
        related_name="received_messages",
    )
    status = models.CharField(
        _("Status"),
        max_length=50,
        null=True,
        blank=True,
        choices=FoiRequest.STATUS.choices,
        default=None,
    )

    timestamp = models.DateTimeField(_("Timestamp"), blank=True)
    last_modified_at = models.DateTimeField(auto_now=True)

    registered_mail_date = models.DateTimeField(
        _("Registered mail date"), blank=True, null=True, default=None
    )  # "Gelber Brief"

    email_message_id = models.CharField(max_length=512, blank=True, default="")
    subject = models.CharField(_("Subject"), blank=True, max_length=255)
    subject_redacted = models.CharField(
        _("Redacted Subject"), blank=True, max_length=255
    )
    plaintext = models.TextField(_("plain text"), blank=True, null=False, default="")
    plaintext_redacted = models.TextField(
        _("redacted plain text"), blank=True, null=True
    )
    html = models.TextField(_("HTML"), blank=True, null=True)
    content_rendered_auth = models.TextField(blank=True, null=True)
    content_rendered_anon = models.TextField(blank=True, null=True)
    redacted_content_auth = models.JSONField(blank=True, null=True)
    redacted_content_anon = models.JSONField(blank=True, null=True)
    redacted = models.BooleanField(_("Was Redacted?"), default=False)
    not_publishable = models.BooleanField(_("Not publishable"), default=False)
    email_headers = models.JSONField(null=True, default=None, blank=True)
    original = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="message_copies",
    )
    tags = TaggableManager(through=TaggedMessage, verbose_name=_("tags"), blank=True)

    confirmation_sent = models.BooleanField(_("Confirmation sent?"), default=False)

    objects = FoiMessageManager()
    no_drafts = FoiMessageNoDraftsManager()

    class Meta:
        get_latest_by = "timestamp"
        ordering = ("timestamp",)
        # order_with_respect_to = 'request'
        verbose_name = _("Freedom of Information Message")
        verbose_name_plural = _("Freedom of Information Messages")

        indexes = [models.Index(fields=["email_message_id"])]

    def __str__(self):
        return _("Message in '%(request)s' at %(time)s") % {
            "request": self.request,
            "time": self.timestamp,
        }

    def save(self, *args, **kwargs):
        if "update_fields" in kwargs:
            kwargs["update_fields"] = {"last_modified_at"}.union(
                kwargs["update_fields"]
            )

        super().save(*args, **kwargs)

    @property
    def is_postal(self):
        return self.kind == MessageKind.POST

    @property
    def is_email(self):
        return self.kind == MessageKind.EMAIL

    @property
    def is_not_email(self):
        return self.kind != MessageKind.EMAIL

    @property
    def can_edit(self):
        return self.kind in MANUAL_MESSAGE_KINDS

    @property
    def received_by_user(self):
        return self.is_response and self.kind in MANUAL_MESSAGE_KINDS

    @property
    def kind_icon(self):
        return MESSAGE_KIND_ICONS.get(self.kind)

    @property
    def content(self):
        return self.plaintext

    @property
    def can_resend_bounce(self):
        if not self.is_email:
            return False
        if self.is_response:
            if self.original_id:
                return self.is_bounce and not self.is_bounce_resent
            return False
        ds = self.get_delivery_status()
        if ds is not None and ds.is_failed():
            return True
        return self.has_bounced

    @property
    def is_bounce(self):
        return self.kind == MessageKind.EMAIL and BOUNCE_TAG in self.tag_set

    @property
    def has_bounced(self):
        return self.kind == MessageKind.EMAIL and HAS_BOUNCED_TAG in self.tag_set

    @property
    def is_bounce_resent(self):
        return BOUNCE_RESENT_TAG in self.tag_set

    @property
    def is_bulk(self):
        return BULK_TAG in self.tag_set

    @cached_property
    def tag_set(self):
        return set(self.tags.all().values_list("name", flat=True))

    @property
    def readable_status(self):
        return FoiRequest.get_readable_status(self.status)

    def get_html_id(self):
        return _("message-%(id)d") % {"id": self.id}

    def get_request_link(self, url):
        return "%s#%s" % (url, self.get_html_id())

    def get_absolute_url(self):
        return self.get_request_link(self.request.get_absolute_url())

    def get_absolute_short_url(self):
        return self.get_request_link(get_absolute_short_url(self.request_id))

    def get_absolute_domain_short_url(self):
        return self.get_request_link(get_absolute_domain_short_url(self.request_id))

    def get_absolute_domain_url(self):
        return self.get_request_link(self.request.get_absolute_domain_url())

    def get_accessible_link(self):
        return self.get_request_link(self.request.get_accessible_link())

    def get_auth_link(self):
        return self.get_request_link(self.request.get_auth_link())

    def get_autologin_url(self):
        return self.get_request_link(self.request.get_autologin_url())

    def get_text_sender(self):
        if self.is_response:
            alternative = self.sender_name
            if self.sender_public_body:
                alternative = self.sender_public_body.name
            if self.is_not_email:
                return _("{name} (via {via})").format(
                    name=self.sender or alternative, via=self.get_kind_display()
                )
            return make_address(self.sender_email, self.sender_name or alternative)

        sender = ""
        sender_user = self.sender_user or self.request.user
        if sender_user:
            sender = sender_user.get_full_name()
        if self.is_not_email:
            return _("{name} (via {via})").format(
                name=sender, via=self.get_kind_display()
            )
        email = self.sender_email or self.request.secret_address
        return make_address(email, sender)

    def get_text_recipient(self):
        if not self.is_response:
            alternative = self.recipient
            if self.recipient_public_body:
                alternative = self.recipient_public_body.name
            if self.is_not_email:
                return _("{name} (via {via})").format(
                    name=self.recipient or alternative, via=self.get_kind_display()
                )
            return make_address(self.recipient_email, self.recipient or alternative)

        recipient = self.recipient or self.request.user.get_full_name()
        if self.is_not_email:
            return _("{name} (via {via})").format(
                name=recipient, via=self.get_kind_display()
            )
        email = self.recipient_email or self.request.secret_address
        return make_address(email, recipient)

    def get_formatted(self, attachments):
        return render_to_string(
            "foirequest/emails/formatted_message.txt",
            {"message": self, "attachments": attachments},
        )

    def get_quoted_message(self):
        header = "\n".join(
            (
                "> {label} 	{value}".format(label=_("Subject:"), value=self.subject),
                "> {label} 	{value}".format(
                    label=_("Date:"),
                    value=formats.date_format(self.timestamp, settings.DATETIME_FORMAT),
                ),
                "> {label} 	{value}".format(
                    label=_("From:"), value=self.get_text_sender()
                ),
                "> {label} 	{value}".format(
                    label=_("To:"), value=self.get_text_recipient()
                ),
            )
        )
        return "{header}\n>\n{text}".format(header=header, text=self.get_quoted_text())

    def get_quoted_text(self):
        return quote_text(self.plaintext)

    def needs_status_input(self):
        return self.request.message_needs_status() == self

    def get_css_class(self):
        if self.is_escalation:
            return "is-escalation"
        if self.is_mediator:
            return "is-mediator"
        if self.is_response:
            return "is-response"
        if self.is_escalation_message:
            return "is-escalation"
        return "is-message"

    @property
    def is_escalation_message(self):
        return self.is_mediator_message(self.recipient_public_body_id)

    @property
    def is_publicbody_response(self):
        return self.is_response and not self.is_mediator

    @property
    def is_mediator(self):
        return self.is_mediator_message(self.sender_public_body_id)

    @property
    def is_default_recipient(self):
        return (
            self.is_email
            and not self.is_response
            and self.request.public_body.email == self.recipient_email
        )

    @property
    def is_default_sender(self):
        return (
            self.is_email
            and self.is_response
            and self.request.public_body.email == self.sender_email
        )

    def is_mediator_message(self, pb_id):
        request = self.request
        if not request.law:
            return None
        if not request.law.mediator_id:
            return None
        if request.law.mediator_id == request.public_body_id:
            # If the request goes to the mediator, we don't know
            return None
        return pb_id == request.law.mediator_id

    @property
    def sender(self) -> str:
        if self.sender_user:
            return self.sender_user.display_name()
        if settings.FROIDE_CONFIG.get("public_body_officials_email_public", False):
            return make_address(self.sender_email, self.sender_name)
        if (
            settings.FROIDE_CONFIG.get("public_body_officials_public", False)
            and self.sender_name
        ):
            return self.sender_name

        if self.sender_public_body:
            return self.sender_public_body.name
        return ""

    @property
    def user_real_sender(self):
        if self.sender_user:
            return self.sender_user.get_full_name()
        if settings.FROIDE_CONFIG.get("public_body_officials_email_public", False):
            return make_address(self.sender_email, self.sender_name)
        if self.sender_name:
            return self.sender_name
        if self.sender_public_body:
            return self.sender_public_body.name
        return ""

    @property
    def real_sender(self):
        if self.sender_user:
            return self.sender_user.get_full_name()
        name = self.sender_name
        if not name and self.sender_public_body:
            name = self.sender_public_body.name
        if self.sender_email:
            name += " <%s>" % self.sender_email
        if self.sender_public_body:
            name += " (%s)" % self.sender_public_body.name
        return name

    @property
    def reply_address_entry(self):
        email = self.sender_email
        pb = None
        if self.sender_public_body:
            pb = self.sender_public_body.name
        if email:
            if pb:
                return "%s (%s)" % (email, pb)
            return email
        else:
            return self.real_sender

    def list_additional_recipients(self):
        from ..utils import get_foi_mail_domains

        if not self.email_headers:
            return []
        recipients = []
        fields = ("to", "cc")
        FOI_EMAIL_DOMAIN = get_foi_mail_domains()[0]
        for field in fields:
            for name, email in self.email_headers.get(field, []):
                # Hide other addresses of foi mail domain
                if email != self.request.secret_address and email.endswith(
                    "@{}".format(FOI_EMAIL_DOMAIN)
                ):
                    recipients.append((field, FOI_EMAIL_DOMAIN, FOI_EMAIL_DOMAIN))
                else:
                    recipients.append((field, name, email))
        return recipients

    def get_extra_content_types(self) -> List[str]:
        prefs = self.email_headers or {}
        return prefs.get("_extra_content_types", [])

    @property
    def attachments(self):
        if not hasattr(self, "_attachments") or self._attachments is None:
            self._attachments = list(self.foiattachment_set.all().order_by("id"))
        return self._attachments

    def get_mime_attachments(self, attachments=None):
        if attachments is None:
            attachments = self.attachments
        return [(a.name, a.get_bytes(), a.filetype) for a in attachments]

    def get_original_attachments(self):
        return [a for a in self.attachments if not a.is_redacted and not a.is_converted]

    def get_subject(self, user=None):
        if self.subject_redacted is None:
            user_replacements = self.request.user.get_redactions()
            self.subject_redacted = redact_subject(self.subject, user_replacements)
            self.save()
        return self.subject_redacted

    def clear_render_cache(self):
        self.content_rendered_auth = None
        self.content_rendered_anon = None
        self.redacted_content_auth = None
        self.redacted_content_anon = None

    def get_content(self):
        self.plaintext = self.plaintext or ""
        if self.plaintext_redacted is None:
            user_replacements = self.request.user.get_redactions()
            self.plaintext_redacted = redact_plaintext(
                self.plaintext,
                redact_closing=self.is_response,
                user_replacements=user_replacements,
            )
            self.clear_render_cache()
            self.save()
        return self.plaintext_redacted

    def get_real_content(self):
        content = self.content
        return content

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.sender_user and self.sender_public_body:
            raise ValidationError("Message may not be from user and public body")

    @classmethod
    def get_throttle_config(cls):
        return settings.FROIDE_CONFIG.get("message_throttle", None)

    @classmethod
    def get_throttle_message(cls):
        return mark_safe(
            _(
                "You exceeded your message limit of %(count)s messages in %(time)s. Find out more in the Help area."
            )
        )

    def get_postal_attachment_form(self):
        from ..forms import get_postal_attachment_form

        return get_postal_attachment_form(foimessage=self)

    def get_public_body_sender_form(self):
        from ..forms import get_message_sender_form

        return get_message_sender_form(foimessage=self)

    def get_public_body_recipient_form(self):
        from ..forms import get_message_recipient_form

        return get_message_recipient_form(foimessage=self)

    def make_message_id(self):
        assert self.id is not None
        assert self.timestamp is not None
        domain = settings.FOI_MAIL_SERVER_HOST
        assert domain and "." in domain
        return "<{}{}.{}@{}>".format(
            MESSAGE_ID_PREFIX, self.id, self.timestamp.timestamp(), domain
        )

    def as_mime_message(self):
        klass = EmailMessage
        if self.html:
            klass = EmailMultiAlternatives

        headers = {
            "Date": formatdate(int(calendar.timegm(self.timestamp.timetuple()))),
            "Message-ID": self.email_message_id,
            "X-Froide-Hint": "replica",
            "X-Froide-Message-Id": self.get_absolute_domain_short_url(),
        }

        if not self.is_response:
            headers.update({"Reply-To": self.sender_email})

        email = klass(
            self.subject,
            self.plaintext,
            self.sender_email,
            to=[self.recipient_email],
            headers=headers,
        )
        if self.html:
            email.attach_alternative(self.html, "text/html")

        atts = self.get_original_attachments()
        mime_atts = self.get_mime_attachments(attachments=atts)
        for mime_data in mime_atts:
            email.attach(*mime_data)
        return email.message()

    def can_get_original_from_imap(self):
        if not self.is_response or not self.is_email:
            return False

        if not self.email_message_id:
            return False
        return True

    def get_original_email_from_imap(self):
        from froide.foirequest.foi_mail import get_foi_mail_client
        from froide.helper.email_utils import retrieve_mail_by_message_id

        if not self.can_get_original_from_imap():
            return

        with get_foi_mail_client() as client:
            data = retrieve_mail_by_message_id(client, self.email_message_id)
        return data

    def fails_authenticity(self):
        if not self.is_response or not self.is_email:
            return
        checks = self.email_headers.get("authenticity")
        if not checks:
            return False
        return any(c["failed"] for c in checks)

    def has_authenticity_info(self):
        return bool(self.email_headers.get("authenticity"))

    def update_email_headers(self, email):
        email_headers = {}
        if email.to and email.to[0].email != self.request.secret_address:
            email_headers["to"] = email.to
        if email.cc:
            email_headers["cc"] = email.cc
        if email.x_original_to:
            email_headers["x_original_to"] = email.x_original_to
        if email.resent_to:
            email_headers["resent-to"] = email.resent_to
        if email.resent_cc:
            email_headers["resent-cc"] = email.resent_cc

        email_headers["authenticity"] = [
            c.to_dict() for c in email.get_authenticity_checks()
        ]

        if email_headers:
            self.email_headers = email_headers
        return email_headers

    def has_delivery_status(self):
        if not self.sent or self.is_response:
            return False
        return self.get_delivery_status() is not None

    def delete_delivery_status(self):
        delattr(self, "_delivery_status")
        ds = self.get_delivery_status()
        if ds is not None:
            ds.delete()
        self._delivery_status = None

    def get_delivery_status(self):
        if hasattr(self, "_delivery_status"):
            return self._delivery_status
        try:
            self._delivery_status = self.deliverystatus
        except DeliveryStatus.DoesNotExist:
            self._delivery_status = None
        return self._delivery_status

    def send(self, **kwargs):
        from ..message_handlers import send_message

        send_message(self, **kwargs)

    def force_resend(self):
        self.resend(force=True)

    def resend(self, **kwargs):
        from ..message_handlers import resend_message
        from ..utils import MailAttachmentSizeChecker

        if "attachments" not in kwargs:
            files = self.get_mime_attachments()
            att_gen = MailAttachmentSizeChecker(files)
            kwargs["attachments"] = list(att_gen)

        resend_message(self, **kwargs)

    def get_redacted_content(self, auth: bool) -> List[Tuple[bool, str]]:
        if auth:
            show, hide, cache_field = (
                self.plaintext,
                self.get_content(),
                "redacted_content_auth",
            )
        else:
            show, hide, cache_field = (
                self.get_content(),
                self.plaintext,
                "redacted_content_anon",
            )

        if getattr(self, cache_field) is None:
            redacted_content = [list(x) for x in get_differences(show, hide)]
            setattr(self, cache_field, redacted_content)
            FoiMessage.objects.filter(id=self.id).update(
                **{cache_field: redacted_content}
            )
        return getattr(self, cache_field)

    def get_cached_rendered_content(self, authenticated_read):
        if authenticated_read:
            return self.content_rendered_auth
        else:
            return self.content_rendered_anon

    def set_cached_rendered_content(self, authenticated_read, content):
        needs_caching = len(self.content) > CONTENT_CACHE_THRESHOLD
        if needs_caching:
            if authenticated_read:
                update = {"content_rendered_auth": content}
            else:
                update = {"content_rendered_anon": content}
            FoiMessage.objects.filter(id=self.id).update(**update)


class Delivery(models.TextChoices):
    STATUS_UNKNOWN = ("unknown", _("unknown"))
    STATUS_SENDING = ("sending", _("sending"))
    STATUS_SENT = ("sent", _("sent"))
    STATUS_RECEIVED = ("received", _("received"))
    STATUS_READ = ("read", _("read"))
    STATUS_DEFERRED = ("deferred", _("deferred"))
    STATUS_BOUNCED = ("bounced", _("bounced"))
    STATUS_EXPIRED = ("expired", _("expired"))
    STATUS_FAILED = ("failed", _("failed"))


class DeliveryStatus(models.Model):
    Delivery = Delivery
    FINAL_STATUS = (
        Delivery.STATUS_SENT,
        Delivery.STATUS_RECEIVED,
        Delivery.STATUS_READ,
        Delivery.STATUS_BOUNCED,
        Delivery.STATUS_EXPIRED,
        Delivery.STATUS_FAILED,
    )

    message = models.OneToOneField(FoiMessage, on_delete=models.CASCADE)
    status = models.CharField(choices=Delivery.choices, blank=True, max_length=32)
    retry_count = models.PositiveIntegerField(default=0)
    log = models.TextField(blank=True)
    last_update = models.DateTimeField(default=timezone.now)

    class Meta:
        get_latest_by = "last_update"
        ordering = ("last_update",)
        verbose_name = _("delivery status")
        verbose_name_plural = _("delivery statii")

    def __str__(self):
        return "%s: %s" % (self.message, self.status)

    def is_sent(self):
        return self.status in (
            Delivery.STATUS_SENT,
            Delivery.STATUS_RECEIVED,
            Delivery.STATUS_READ,
        )

    def is_pending(self):
        return self.status in (Delivery.STATUS_DEFERRED, Delivery.STATUS_SENDING)

    def is_failed(self):
        return self.status in (
            Delivery.STATUS_BOUNCED,
            Delivery.STATUS_EXPIRED,
            Delivery.STATUS_FAILED,
        )

    def is_log_status_final(self):
        return self.status in self.FINAL_STATUS
