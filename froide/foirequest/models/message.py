from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.encoding import python_2_unicode_compatible

from froide.publicbody.models import PublicBody
from froide.account.services import AccountService
from froide.helper.email_utils import make_address
from froide.helper.text_utils import (redact_content, remove_closing, replace_custom)

from ..foi_mail import send_foi_mail
from .request import FoiRequest


class FoiMessageManager(models.Manager):
    def get_throttle_filter(self, user):
        return self.get_queryset().filter(sender_user=user), 'timestamp'


@python_2_unicode_compatible
class FoiMessage(models.Model):
    request = models.ForeignKey(FoiRequest,
            verbose_name=_("Freedom of Information Request"),
            on_delete=models.CASCADE)
    sent = models.BooleanField(_("has message been sent?"), default=True)
    is_response = models.BooleanField(_("Is this message a response?"),
            default=True)
    is_postal = models.BooleanField(_("Postal?"),
            default=False)
    is_escalation = models.BooleanField(_("Escalation?"),
            default=False)
    content_hidden = models.BooleanField(_("Content hidden?"),
            default=False)
    sender_user = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            blank=True,
            null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("From User")
    )
    sender_email = models.CharField(_("From Email"),
            blank=True, max_length=255)
    sender_name = models.CharField(_("From Name"),
            blank=True, max_length=255)
    sender_public_body = models.ForeignKey(PublicBody, blank=True,
            null=True, on_delete=models.SET_NULL,
            verbose_name=_("From Public Body"), related_name='send_messages')

    recipient = models.CharField(_("Recipient"), max_length=255,
            blank=True, null=True)
    recipient_email = models.CharField(_("Recipient Email"), max_length=255,
            blank=True, null=True)
    recipient_public_body = models.ForeignKey(PublicBody, blank=True,
            null=True, on_delete=models.SET_NULL,
            verbose_name=_("Public Body Recipient"), related_name='received_messages')
    status = models.CharField(_("Status"), max_length=50, null=True, blank=True,
            choices=FoiRequest.STATUS_FIELD_CHOICES, default=None)

    timestamp = models.DateTimeField(_("Timestamp"), blank=True)
    subject = models.CharField(_("Subject"), blank=True, max_length=255)
    subject_redacted = models.CharField(_("Redacted Subject"), blank=True, max_length=255)
    plaintext = models.TextField(_("plain text"), blank=True, null=True)
    plaintext_redacted = models.TextField(_("redacted plain text"), blank=True, null=True)
    html = models.TextField(_("HTML"), blank=True, null=True)
    original = models.TextField(_("Original"), blank=True)
    redacted = models.BooleanField(_("Was Redacted?"), default=False)
    not_publishable = models.BooleanField(_('Not publishable'), default=False)

    objects = FoiMessageManager()

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ('timestamp',)
        # order_with_respect_to = 'request'
        verbose_name = _('Freedom of Information Message')
        verbose_name_plural = _('Freedom of Information Messages')

    @property
    def content(self):
        return self.plaintext

    def __str__(self):
        return _("Message in '%(request)s' at %(time)s"
                ) % {"request": self.request,
                    "time": self.timestamp}

    @property
    def readable_status(self):
        return FoiRequest.get_readable_status(self.status)

    def get_html_id(self):
        return _("message-%(id)d") % {"id": self.id}

    def get_absolute_url(self):
        return "%s#%s" % (self.request.get_absolute_url(),
                self.get_html_id())

    def get_absolute_short_url(self):
        return "%s#%s" % (self.request.get_absolute_short_url(),
                self.get_html_id())

    def get_absolute_domain_short_url(self):
        return "%s#%s" % (self.request.get_absolute_domain_short_url(),
                          self.get_html_id())

    def get_absolute_domain_url(self):
        return "%s#%s" % (self.request.get_absolute_domain_url(),
                self.get_html_id())

    def get_accessible_link(self):
        return "%s#%s" % (self.request.get_accessible_link(),
                self.get_html_id())

    def get_public_body_sender_form(self):
        from froide.foirequest.forms import MessagePublicBodySenderForm
        return MessagePublicBodySenderForm(self)

    def get_text_recipient(self):
        if not self.is_response:
            alternative = self.recipient
            if self.recipient_public_body:
                alternative = self.recipient_public_body.name
            if self.is_postal:
                return _('{} (via post)').format(self.recipient or alternative)
            return make_address(self.recipient_email,
                    self.recipient or alternative)

        recipient = self.recipient or self.request.user.get_full_name()
        if self.is_postal:
            return _('{} (via post)').format(recipient)
        return make_address(self.recipient_email or self.request.secret_address,
                            recipient)

    def get_recipient(self):
        if self.recipient_public_body:
            return mark_safe('<a href="%(url)s">%(name)s</a>' % {
                "url": self.recipient_public_body.get_absolute_url(),
                "name": escape(self.recipient_public_body.name)})
        else:
            return self.recipient

    def get_formated(self, attachments):
        return render_to_string('foirequest/emails/formated_message.txt', {
                'message': self,
                'attachments': attachments
        })

    def get_quoted(self):
        return "\n".join([">%s" % l for l in self.plaintext.splitlines()])

    def needs_status_input(self):
        return self.request.message_needs_status() == self

    @property
    def sender(self):
        if self.sender_user:
            return self.sender_user.display_name()
        if settings.FROIDE_CONFIG.get("public_body_officials_email_public",
                False):
            return make_address(self.sender_email, self.sender_name)
        if settings.FROIDE_CONFIG.get("public_body_officials_public",
                False) and self.sender_name:
            return self.sender_name
        else:
            if self.sender_public_body:
                return self.sender_public_body.name
            return self.sender_public_body

    @property
    def user_real_sender(self):
        if self.sender_user:
            return self.sender_user.display_name()
        if settings.FROIDE_CONFIG.get("public_body_officials_email_public",
                False):
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
        if not hasattr(self, "_attachments"):
            self._attachments = list(self.foiattachment_set.all())
        return self._attachments

    def get_subject(self, user=None):
        if self.subject_redacted is None:
            self.subject_redacted = self.redact_subject()
            self.save()
        return self.subject_redacted

    def redact_subject(self):
        content = self.subject
        if self.request.user:
            account_service = AccountService(self.request.user)
            content = account_service.apply_message_redaction(content)
        content = redact_content(content)
        return content[:255]

    def get_content(self):
        if self.plaintext_redacted is None:
            self.plaintext_redacted = self.redact_plaintext()
            self.save()
        return self.plaintext_redacted

    def get_content_check(self):
        return self.get_content() if not self.content_hidden else None

    def redact_plaintext(self):
        content = self.plaintext

        content = redact_content(content)

        greeting_replacement = str(_("<< Greeting >>"))

        if not settings.FROIDE_CONFIG.get('public_body_officials_public'):
            if self.is_response:
                if settings.FROIDE_CONFIG.get('closings'):
                    content = remove_closing(settings.FROIDE_CONFIG['closings'],
                                             content)

            else:
                if settings.FROIDE_CONFIG.get('greetings'):
                    content = replace_custom(settings.FROIDE_CONFIG['greetings'],
                            greeting_replacement, content)

        if self.request.user:
            account_service = AccountService(self.request.user)
            content = account_service.apply_message_redaction(content)

        return content

    def get_real_content(self):
        content = self.content
        return content

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.sender_user and self.sender_public_body:
            raise ValidationError(
                    'Message may not be from user and public body')

    def get_postal_attachment_form(self):
        from froide.foirequest.forms import PostalAttachmentForm
        return PostalAttachmentForm()

    def send(self, notify=True, attachments=None):
        extra_kwargs = {}
        if settings.FROIDE_CONFIG['dryrun']:
            recp = self.recipient_email.replace("@", "+")
            self.recipient_email = "%s@%s" % (recp, settings.FROIDE_CONFIG['dryrun_domain'])
        # Use send_foi_mail here
        from_addr = make_address(self.request.secret_address,
                self.request.user.get_full_name())
        delivery_notification = (self.sender_user.is_superuser and
                                  not self.request.public)
        if settings.FROIDE_CONFIG['read_receipt'] and delivery_notification:
            extra_kwargs['read_receipt'] = True
        if settings.FROIDE_CONFIG['delivery_receipt'] and delivery_notification:
            extra_kwargs['delivery_receipt'] = True
        if settings.FROIDE_CONFIG['dsn'] and delivery_notification:
            extra_kwargs['dsn'] = True
        extra_kwargs['froide_message_id'] = self.get_absolute_domain_short_url()

        if not self.request.is_blocked:
            send_foi_mail(self.subject, self.plaintext, from_addr,
                    [self.recipient_email.strip()], attachments=attachments, **extra_kwargs)
            self.sent = True
            self.save()
        self.request._messages = None
        if notify:
            FoiRequest.message_sent.send(sender=self.request, message=self)
