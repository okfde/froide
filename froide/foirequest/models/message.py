from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import format_html

from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase

from froide.publicbody.models import PublicBody
from froide.helper.email_utils import make_address
from froide.helper.text_utils import (
    redact_subject, redact_plaintext
)

from ..utils import MailAttachmentSizeChecker
from .request import FoiRequest, get_absolute_short_url


class FoiMessageManager(models.Manager):
    def get_throttle_filter(self, queryset, user, extra_filters=None):
        qs = queryset.filter(
            sender_user=user, is_response=False
        )
        if extra_filters is not None:
            qs = qs.filter(**extra_filters)
        return qs, 'timestamp'


class MessageTag(TagBase):
    class Meta:
        verbose_name = _("message tag")
        verbose_name_plural = _("message tags")


class TaggedMessage(TaggedItemBase):
    tag = models.ForeignKey(
        MessageTag, on_delete=models.CASCADE,
        related_name="tagged_messages")
    content_object = models.ForeignKey('FoiMessage', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('tagged message')
        verbose_name_plural = _('tagged messages')


class FoiMessage(models.Model):
    MESSAGE_CHOICES = (
        ('email', _('Email')),
        ('post', _('Postal mail')),
        ('fax', _('Fax')),
        ('upload', _('Upload')),
        ('phone', _('Phone call')),
        ('visit', _('Personal visit')),
    )
    request = models.ForeignKey(
        FoiRequest,
        verbose_name=_("Freedom of Information Request"),
        on_delete=models.CASCADE)
    sent = models.BooleanField(_("has message been sent?"), default=True)
    is_response = models.BooleanField(
        _("response?"),
        default=True)
    kind = models.CharField(
        max_length=10, choices=MESSAGE_CHOICES,
        default='email'
    )
    is_escalation = models.BooleanField(
        _("Escalation?"),
        default=False)
    content_hidden = models.BooleanField(
        _("Content hidden?"),
        default=False)
    sender_user = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            blank=True,
            null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("From User")
    )
    sender_email = models.CharField(
        _("From Email"),
        blank=True, max_length=255)
    sender_name = models.CharField(
        _("From Name"),
        blank=True, max_length=255)
    sender_public_body = models.ForeignKey(
        PublicBody, blank=True,
        null=True, on_delete=models.SET_NULL,
        verbose_name=_("From Public Body"), related_name='send_messages')

    recipient = models.CharField(
        _("Recipient"), max_length=255,
        blank=True, null=True)
    recipient_email = models.CharField(
        _("Recipient Email"), max_length=255,
        blank=True, null=True)
    recipient_public_body = models.ForeignKey(
        PublicBody, blank=True,
        null=True, on_delete=models.SET_NULL,
        verbose_name=_("Public Body Recipient"),
        related_name='received_messages')
    status = models.CharField(
        _("Status"), max_length=50, null=True, blank=True,
        choices=FoiRequest.STATUS_FIELD_CHOICES, default=None)

    timestamp = models.DateTimeField(_("Timestamp"), blank=True)
    email_message_id = models.CharField(max_length=512, blank=True, default='')
    subject = models.CharField(_("Subject"), blank=True, max_length=255)
    subject_redacted = models.CharField(
        _("Redacted Subject"), blank=True, max_length=255)
    plaintext = models.TextField(_("plain text"), blank=True, null=True)
    plaintext_redacted = models.TextField(
        _("redacted plain text"), blank=True, null=True)
    html = models.TextField(_("HTML"), blank=True, null=True)
    redacted = models.BooleanField(_("Was Redacted?"), default=False)
    not_publishable = models.BooleanField(_('Not publishable'), default=False)
    original = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='message_copies'
    )
    tags = TaggableManager(
        through=TaggedMessage,
        verbose_name=_('tags'),
        blank=True
    )

    objects = FoiMessageManager()

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ('timestamp',)
        # order_with_respect_to = 'request'
        verbose_name = _('Freedom of Information Message')
        verbose_name_plural = _('Freedom of Information Messages')

    def __str__(self):
        return _(
            "Message in '%(request)s' at %(time)s") % {
                "request": self.request,
                "time": self.timestamp
            }

    @property
    def is_postal(self):
        return self.kind == 'post'

    @property
    def is_not_email(self):
        return self.kind != 'email'

    @property
    def can_edit(self):
        return self.is_response and self.is_not_email

    @property
    def content(self):
        return self.plaintext

    @property
    def readable_status(self):
        return FoiRequest.get_readable_status(self.status)

    def get_html_id(self):
        return _("message-%(id)d") % {"id": self.id}

    def get_request_link(self, url):
        return '%s#%s' % (url, self.get_html_id())

    def get_absolute_url(self):
        return self.get_request_link(self.request.get_absolute_url())

    def get_absolute_short_url(self):
        return self.get_request_link(get_absolute_short_url(self.request_id))

    def get_absolute_domain_short_url(self):
        return self.get_request_link(self.request.get_absolute_domain_short_url())

    def get_absolute_domain_url(self):
        return self.get_request_link(self.request.get_absolute_domain_url())

    def get_accessible_link(self):
        return self.get_request_link(self.request.get_accessible_link())

    def get_auth_link(self):
        return self.get_request_link(self.request.get_auth_link())

    def get_autologin_url(self):
        return self.get_request_link(self.request.get_autologin_url())

    def get_text_recipient(self):
        if not self.is_response:
            alternative = self.recipient
            if self.recipient_public_body:
                alternative = self.recipient_public_body.name
            if self.is_not_email:
                return _('{name} (via {via})').format(
                    name=self.recipient or alternative,
                    via=self.get_kind_display()
                )
            return make_address(self.recipient_email,
                                self.recipient or alternative)

        recipient = self.recipient or self.request.user.get_full_name()
        if self.is_not_email:
            return _('{name} (via {via})').format(
                name=recipient,
                via=self.get_kind_display()
            )
        email = self.recipient_email or self.request.secret_address
        return make_address(email, recipient)

    def get_recipient(self):
        if self.recipient_public_body:
            return format_html(
                '<a href="{url}">{name}</a>',
                url=self.recipient_public_body.get_absolute_url(),
                name=self.recipient_public_body.name
            )
        else:
            return self.recipient

    def get_formatted(self, attachments):
        return render_to_string('foirequest/emails/formatted_message.txt', {
                'message': self,
                'attachments': attachments
        })

    def get_quoted(self):
        return "\n".join([">%s" % l for l in self.plaintext.splitlines()])

    def needs_status_input(self):
        return self.request.message_needs_status() == self

    def get_css_class(self):
        if self.is_escalation:
            return 'is-escalation'
        if self.is_mediator:
            return 'is-mediator'
        if self.is_response:
            return 'is-response'
        if self.is_escalation_message:
            return 'is-escalation'
        return 'is-message'

    @property
    def is_escalation_message(self):
        return self.is_mediator_message(self.recipient_public_body_id)

    @property
    def is_publicbody_response(self):
        return self.is_response and not self.is_mediator

    @property
    def is_mediator(self):
        return self.is_mediator_message(self.sender_public_body_id)

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
    def sender(self):
        if self.sender_user:
            return self.sender_user.display_name()
        if settings.FROIDE_CONFIG.get(
                "public_body_officials_email_public", False):
            return make_address(self.sender_email, self.sender_name)
        if settings.FROIDE_CONFIG.get(
                "public_body_officials_public", False) and self.sender_name:
            return self.sender_name
        else:
            if self.sender_public_body:
                return self.sender_public_body.name
            return self.sender_public_body

    @property
    def user_real_sender(self):
        if self.sender_user:
            return self.sender_user.get_full_name()
        if settings.FROIDE_CONFIG.get(
                "public_body_officials_email_public", False):
            return make_address(self.sender_email, self.sender_name)
        if self.sender_name:
            return self.sender_name
        else:
            if self.sender_public_body:
                return self.sender_public_body.name
            return self.sender_public_body

    @property
    def real_sender(self):
        if self.sender_user:
            return self.sender_user.get_full_name()
        name = self.sender_name
        if not name and self.sender_public_body:
            name = self.sender_public_body.name
        if self.sender_email:
            name += ' <%s>' % self.sender_email
        if self.sender_public_body:
            name += ' (%s)' % self.sender_public_body.name
        return name

    @property
    def reply_address_entry(self):
        email = self.sender_email
        pb = None
        if self.sender_public_body:
            pb = self.sender_public_body.name
        if email:
            if pb:
                return '%s (%s)' % (email, pb)
            return email
        else:
            return self.real_sender

    @property
    def attachments(self):
        if not hasattr(self, '_attachments') or self._attachments is None:
            self._attachments = list(self.foiattachment_set.all().order_by('id'))
        return self._attachments

    def get_mime_attachments(self):
        return [(a.name, a.get_bytes(), a.filetype) for a in self.attachments]

    def get_original_attachments(self):
        return [a for a in self.attachments if not a.is_redacted and not a.is_converted]

    def get_subject(self, user=None):
        if self.subject_redacted is None:
            self.subject_redacted = redact_subject(
                self.subject, user=self.request.user
            )
            self.save()
        return self.subject_redacted

    def get_content(self):
        self.plaintext = self.plaintext or ''
        if self.plaintext_redacted is None:
            self.plaintext_redacted = redact_plaintext(
                self.plaintext,
                self.is_response,
                user=self.request.user
            )
            self.save()
        return self.plaintext_redacted

    def get_real_content(self):
        content = self.content
        return content

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.sender_user and self.sender_public_body:
            raise ValidationError(
                    'Message may not be from user and public body')

    @classmethod
    def get_throttle_config(cls):
        return settings.FROIDE_CONFIG.get('message_throttle', None)

    def get_postal_attachment_form(self):
        from ..forms import get_postal_attachment_form
        return get_postal_attachment_form(foimessage=self)

    def get_public_body_sender_form(self):
        from ..forms import get_message_sender_form
        return get_message_sender_form(foimessage=self)

    def has_delivery_status(self):
        if not self.sent or self.is_response:
            return False
        return self.get_delivery_status() is not None

    def delete_delivery_status(self):
        self._delivery_status = None
        ds = self.get_delivery_status()
        if ds is not None:
            ds.delete()
        self._delivery_status = None

    def get_delivery_status(self):
        if hasattr(self, '_delivery_status') and self._delivery_status is None:
            return self._delivery_status
        try:
            self._delivery_status = self.deliverystatus
        except DeliveryStatus.DoesNotExist:
            self._delivery_status = None
        return self._delivery_status

    def check_delivery_status(self, count=None, extended=False):
        if self.is_not_email or self.is_response:
            return
        if not self.sender_email or not self.recipient_email:
            return

        from froide.foirequest.delivery import get_delivery_report
        from ..tasks import check_delivery_status

        report = get_delivery_report(
            self.sender_email, self.recipient_email, self.timestamp,
            extended=extended
        )
        if report is None:
            if count is None or count > 5:
                return
            count += 1
            check_delivery_status.apply_async((self.id,), {'count': count},
                                              countdown=5**count * 60)
            return

        if not self.email_message_id and report.message_id:
            self.email_message_id = report.message_id
            self.save()

        ds, created = DeliveryStatus.objects.update_or_create(
            message=self,
            defaults=dict(
                log=report.log,
                status=report.status,
                last_update=timezone.now(),
            )
        )
        if count is None or count > 5:
            return

        count += 1
        if not ds.is_log_status_final():
            check_delivery_status.apply_async(
                (self.id,),
                {'count': count},
                countdown=5**count * 60
            )

    def send(self, notify=True, **kwargs):
        from ..message_handlers import send_message

        send_message(self, notify=notify, **kwargs)

    def force_resend(self):
        self.delete_delivery_status()
        self.resend()

    def resend(self, **kwargs):
        from ..message_handlers import resend_message

        if 'attachments' not in kwargs:
            files = self.get_mime_attachments()
            att_gen = MailAttachmentSizeChecker(files)
            kwargs['attachments'] = list(att_gen)

        resend_message(self, **kwargs)


class DeliveryStatus(models.Model):
    STATUS_UNKNOWN = 'unknown'
    STATUS_SENDING = 'sending'
    STATUS_SENT = 'sent'
    STATUS_RECEIVED = 'received'
    STATUS_READ = 'read'
    STATUS_DEFERRED = 'deferred'
    STATUS_BOUNCED = 'bounced'
    STATUS_EXPIRED = 'expired'
    STATUS_FAILED = 'failed'

    FINAL_STATUS = (
        STATUS_SENT, STATUS_RECEIVED, STATUS_READ, STATUS_BOUNCED,
        STATUS_EXPIRED, STATUS_FAILED
    )

    STATUS_CHOICES = (
        (STATUS_UNKNOWN, _('unknown')),
        (STATUS_SENDING, _('sending')),
        (STATUS_SENT, _('sent')),
        (STATUS_RECEIVED, _('received')),
        (STATUS_READ, _('read')),
        (STATUS_DEFERRED, _('deferred')),
        (STATUS_BOUNCED, _('bounced')),
        (STATUS_EXPIRED, _('expired')),
        (STATUS_FAILED, _('failed')),
    )

    message = models.OneToOneField(FoiMessage, on_delete=models.CASCADE)
    status = models.CharField(choices=STATUS_CHOICES, blank=True, max_length=32)
    retry_count = models.PositiveIntegerField(default=0)
    log = models.TextField(blank=True)
    last_update = models.DateTimeField()

    class Meta:
        get_latest_by = 'last_update'
        ordering = ('last_update',)
        verbose_name = _('delivery status')
        verbose_name_plural = _('delivery statii')

    def __str__(self):
        return '%s: %s' % (self.message, self.status)

    def is_sent(self):
        return self.status in (
            self.STATUS_SENT,
            self.STATUS_RECEIVED,
            self.STATUS_READ
        )

    def is_pending(self):
        return self.status in (
            self.STATUS_DEFERRED, self.STATUS_SENDING
        )

    def is_failed(self):
        return self.status in (
            self.STATUS_BOUNCED, self.STATUS_EXPIRED, self.STATUS_FAILED
        )

    def is_log_status_final(self):
        return self.status in self.FINAL_STATUS
