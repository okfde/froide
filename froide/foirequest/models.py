import random
from datetime import datetime
import json

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.core.urlresolvers import reverse
from django.core.files import File
import django.dispatch
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.timesince import timesince

from mailer import send_mail

from publicbody.models import PublicBody, FoiLaw
from froide.helper.date_utils import convert_to_local
from froide.helper.text_utils import (replace_email_name, 
        replace_email, remove_signature, remove_quote)

html2markdown = lambda x: x


class FoiRequestManager(CurrentSiteManager):
    def get_for_homepage(self, count=5):
        return self.get_query_set()[:count]

    def related_from_slug(self, slug):
        return self.get_query_set().filter(slug=slug).select_related()

    def get_by_secret_mail(self, mail):
        return self.get_query_set().get(secret_address=mail)

    def get_for_search_index(self):
        return self.get_query_set().filter(visibility=2)


class FoiRequest(models.Model):
    ADMIN_SET_CHOICES = (
        ('awaiting_user_confirmation', _('Awaiting user confirmation')),
        ('publicbody_needed', _('Public Body needed')),
        ('awaiting_publicbody_confirmation', _('Awaiting Public Body confirmation')),
        ('overdue', _('Response overdue')),
    )
    USER_SET_CHOICES = (
        ('awaiting_response', _('Awaiting response')),
        ('awaiting_clarification', _('Awaiting clarification from Public Body')),
        ('awaiting_clarification_from_requester', _('Awaiting clarification from Requester')),
        ('requires_admin', _('Requires administrative action')),
        ('gone_postal', _('Gone Postal')),
        ('not_held', _('Information not held')),
        ('refused', _('Request refused')),
        ('successful', _('Request Successful')),
        ('partially_successful', _('Request partially successful')),
        ('escalation', _('Escalate Request')),
        ('error_message', _('Error Occured')),
        ('user_withdrawn', _('User withdrew request')),
    )

    if settings.FROIDE_CONFIG.get('payment_possible'):
        USER_SET_CHOICES += (('requires_payment', _('Costs specified')),
                ('payment_refused', _('Payment refused')),
                ('payment_accepted', _('Payment accepted'))
            )

    STATUS_CHOICES = ADMIN_SET_CHOICES + USER_SET_CHOICES
    STATUS_CHOICES_DICT = dict(STATUS_CHOICES)

    VISIBILITY_CHOICES = (
        (0, _("Invisible")),
        (1, _("Visible to Requester")),
        (2, _("Public")),
    )


    title = models.CharField(_("Title"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    public_body = models.ForeignKey(PublicBody, null=True, blank=True,
            on_delete=models.SET_NULL, verbose_name=_("Public Body"))

    public = models.BooleanField(_("published?"), default=True)

    status = models.CharField(max_length=25, choices=STATUS_CHOICES)
    visibility = models.SmallIntegerField(default=0, choices=VISIBILITY_CHOICES)
    
    user = models.ForeignKey(User, null=True,
            on_delete=models.SET_NULL)

    first_message = models.DateTimeField(blank=True, null=True)
    last_message = models.DateTimeField(blank=True, null=True)
    resolved_on = models.DateTimeField(blank=True, null=True)
    
    secret_address = models.CharField(max_length=255,
            db_index=True, unique=True)
    secret = models.CharField(blank=True, max_length=100)

    law = models.ForeignKey(FoiLaw, null=True, blank=True,
            on_delete=models.SET_NULL)
    costs = models.FloatField(_("Cost of Information"), default=0.0)
    refusal_reason = models.CharField(max_length=255, blank=True)
    
    site = models.ForeignKey(Site, null=True,
            on_delete=models.SET_NULL)
    
    objects = FoiRequestManager()

    class Meta:
        ordering = ('last_message',)
        get_latest_by = 'last_message'
        verbose_name = _('Freedom of Information Request')
        verbose_name_plural = _('Freedom of Information Requests')

    # Custom Signals
    message_received = django.dispatch.Signal(providing_args=["message"])
    request_created = django.dispatch.Signal(providing_args=[])
    status_changed = django.dispatch.Signal(providing_args=["status", "data"])

    def __unicode__(self):
        return u"Request '%s'" % self.title

    @property
    def messages(self):
        if not hasattr(self, "_messages"):
            self._messages = self.foimessage_set.all().select_related()
        return self._messages

    @property
    def status_settable(self):
        return len(self.messages) > 1

    def get_absolute_url(self):
        return reverse('foirequest-show',
                kwargs={'slug': self.slug})

    def is_visible(self, user):
        if self.visibility == 0:
            return False
        if self.visibility == 2:
            return True
        if self.visibility == 1 and (
                user.is_authenticated() and 
                self.user == user):
            return True
        return False

    def status_form_klass(self):
        from foirequest.forms import get_status_form_class
        return get_status_form_class(self)

    def status_form(self):
        if not hasattr(self, "_status_form"):
            self._status_form = self.status_form_klass()(
                    initial={"status": self.status,
                        "costs": self.costs,
                        "refusal_reason": self.refusal_reason})
        return self._status_form

    def set_status(self, data):
        self.status = data['status']
        if settings.FROIDE_CONFIG.get('payment_possible'):
            self.costs = data['costs']
        if self.status == "refused":
            self.refusal_reason = data['refusal_reason']
        self.save()
        status = data.pop("status")
        self.status_changed.send(sender=self, status=status, data=data)

    def public_body_suggestions(self):
        return PublicBodySuggestion.objects.filter(request=self)

    def public_body_suggestions_form_klass(self):
        from foirequest.forms import get_public_body_suggestions_form_class
        return get_public_body_suggestions_form_class(
            self.public_body_suggestions())

    def public_body_suggestions_form(self):
        if not hasattr(self, "_public_body_suggestion_form"):
            self._public_body_suggestion_form = self.public_body_suggestions_form_klass()()
        return self._public_body_suggestion_form

    def add_message_from_email(self, email, mail_string):
        message = FoiMessage(request=self)
        message.subject = email['subject']
        message.is_response = True
        message.sender_name = email['from'][0]
        message.sender_email = email['from'][1]
        message.sender_public_body = self.public_body
        message.timestamp = convert_to_local(*email['date'])
        message.plaintext = email['body']
        message.html = html2markdown(email['html'])
        message.original = mail_string
        message.save()
        self.last_message = message.timestamp
        self.save()

        for attachment in email['attachments']:
            att = FoiAttachment(belongs_to=message,
                    name=attachment.name,
                    size=attachment.size,
                    filetype=attachment.content_type)
            attachment._committed = False
            att.file = File(attachment)
            att.save()
        self.message_received.send(sender=self, message=message)

    @classmethod
    def generate_secret_address(cls, user):
        possible_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        secret = "".join([random.choice(possible_chars) for i in range(10)])
        return "%s+%s@%s" % (user.username, secret, settings.FOI_MAIL_DOMAIN)

    @property
    def readable_status(self):
        return self.STATUS_CHOICES_DICT.get(self.status, _("Unknown"))

    @classmethod
    def from_request_form(cls, user, public_body_object, foi_law, **request_form):
        now = datetime.now()
        request = FoiRequest(title=request_form['subject'],
                public_body=public_body_object,
                user=user,
                site=Site.objects.get_current(),
                first_message=now,
                last_message=now)
        send_now = False
        if not user.is_active:
            request.status = 'awaiting_user_confirmation'
            request.visibility = 0
        else:
            if request.public:
                request.visibility = 2
            else:
                request.visibility = 1
            if public_body_object is None:
                request.status = 'publicbody_needed'
            elif not public_body_object.confirmed:
                request.status = 'awaiting_publicbody_confirmation'
            else:
                request.status = 'awaiting_response'
                send_now = True

        #TODO: ensure uniqueness of address
        request.secret_address = cls.generate_secret_address(user)
        #TODO: add right law
        request.law = foi_law
        #TODO: ensure slug unique
        request.slug = slugify(request.title)
        request.save()
        message = FoiMessage(request=request,
                sent=False,
                is_response=False,
                sender_user=user,
                sender_email=request.secret_address,
                sender_name=user.get_full_name(),
                timestamp=now,
                subject=request.title)
        if public_body_object is not None:
            message.recipient = public_body_object.email
        message.plaintext = cls.construct_message_body(message,
                request_form['body'])
        message.original = message.plaintext
        message.save()
        cls.request_created.send(sender=request)
        if send_now:
            message.send()
        return request

    @classmethod
    def construct_message_body(cls, message, body):
        return render_to_string("foirequest/foi_request_mail.txt",
                {"message": message, "body": body})

    def set_status_after_change(self):
        if not self.user.is_active:
            self.status = "awaiting_user_confirmation"
        if self.public_body is None:
            self.status = 'publicbody_needed'
        elif not self.public_body.confirmed:
            self.status = 'awaiting_publicbody_confirmation'
        else:
            self.status = 'awaiting_response'
            return True
        return False

    @classmethod
    def confirmed_request(cls, user, request_id):
        try:
            request = FoiRequest.objects.get(pk=request_id)
        except FoiRequest.DoesNotExist:
            return None
        if not request.user == user:
            return None
        sent_now = request.set_status_after_change()
        request.save()
        messages = request.foimessage_set.all()
        if not len(messages) == 1:
            return None
        message = messages[0]
        if message.sent:
            return None
        if sent_now:
            message.send()
            return request
        return None

    def set_public_body(self, public_body, law):
        assert self.public_body == None
        assert self.status == "publicbody_needed"
        self.public_body = public_body
        self.law = law
        sent_now = self.set_status_after_change()
        self.save()
        if sent_now:
            messages = self.foimessage_set.all()
            assert len(messages) == 1
            message = messages[0]
            message.recipient = public_body.email
            assert message.sent == False
            message.send() # saves message


class PublicBodySuggestion(models.Model):
    request = models.ForeignKey(FoiRequest)
    public_body = models.ForeignKey(PublicBody)
    user = models.ForeignKey(User, null=True,
            on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)


class FoiMessage(models.Model):
    request = models.ForeignKey(FoiRequest)
    sent = models.BooleanField(default=True)
    is_response = models.BooleanField(default=True)
    sender_user = models.ForeignKey(User, blank=True, null=True,
            on_delete=models.SET_NULL)
    sender_email = models.CharField(blank=True, max_length=255)
    sender_name = models.CharField(blank=True, max_length=255)
    sender_public_body = models.ForeignKey(PublicBody, blank=True,
            null=True, on_delete=models.SET_NULL)
    recipient = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(blank=True)
    subject = models.CharField(blank=True, max_length=255)
    plaintext = models.TextField(blank=True, null=True)
    html = models.TextField(blank=True, null=True)
    original = models.TextField(blank=True)
    redacted = models.BooleanField(default=False)

    _status = models.SmallIntegerField(null=True, default=None, blank=True)
    _resolution = models.SmallIntegerField(null=True, default=None, blank=True)
    _visibility = models.SmallIntegerField(default=1)

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ('timestamp',)
        # order_with_respect_to = 'request'
        verbose_name = _('Freedom of Information Message')
        verbose_name_plural = _('Freedom of Information Messages')

    message_sent = django.dispatch.Signal(providing_args=[])


    @property
    def content(self):
        return self.plaintext

    def __unicode__(self):
        return u"Message in '%s' at %s" % (self.request,
                self.timestamp)

    @property
    def sender(self):
        if self.sender_user:
            return self.sender_user.get_full_name()
        else:
            return self.sender_public_body.name

    @property
    def attachments(self):
        if not hasattr(self, "_attachments"):
            self._attachments = list(self.foiattachment_set.all())
        return self._attachments

    def get_content(self):
        content = self.content
        # content = remove_quote(content, replacement=_(u"Quoted part removed"))
        content = replace_email_name(content)
        content = replace_email(content)
        content = remove_signature(content)
        content = remove_quote(content)
        return content

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.sender_user and self.sender_public_body:
            raise ValidationError(
                    'Message may not be from user and public body')

    def send(self):
        send_mail(self.subject, self.plaintext,
                self.request.secret_address, [self.recipient])
        self.sent = True
        self.save()
        self.message_sent.send(sender=self)


@receiver(FoiMessage.message_sent, dispatch_uid="send_foimessage_sent_confirmation")
def send_foimessage_sent_confirmation(sender, **kwargs):
    send_mail(_("Your Freedom of Information Request"), 
            "", #FIXME: render_to_string(),
            settings.DEFAULT_FROM_EMAIL,
            [sender.sender_user.email])


def upload_to(instance, filename):
    return "foi/%s/%s" % (instance.belongs_to.id, filename)


class FoiAttachment(models.Model):
    belongs_to = models.ForeignKey(FoiMessage, null=True,
            on_delete=models.SET_NULL)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=upload_to)
    size = models.IntegerField(blank=True, null=True)
    filetype = models.CharField(blank=True, max_length=100)
    format = models.CharField(blank=True, max_length=100)
    
    class Meta:
        ordering = ('name',)
        # order_with_respect_to = 'belongs_to'
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')

    def __unicode__(self):
        return u"%s (%s) of %s" % (self.name, self.size, self.belongs_to)

    def viewable(self):
        return False


class FoiEvent(models.Model):
    request = models.ForeignKey(FoiRequest)
    user = models.ForeignKey(User, null=True,
            on_delete=models.SET_NULL)
    public_body = models.ForeignKey(PublicBody, null=True,
            on_delete=models.SET_NULL)
    event_name = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    context_json = models.TextField()

    html_events = {
        "reported_costs": _(
            u"%(user)s reported costs of %(amount)s for this request.")
    }

    plaintext_events = {

    }

    def get_context(self):
        context = getattr(self, "_context", None)
        if context is not None:
            return context
        context = json.loads(self.context_json)
        context.update({"user": self.user, "public_body": self.public_body,
            "since": timesince(self.timestamp), "date": self.timestamp})
        self._context = context
        return context
    
    @property
    def html(self):
        return self.html_events[self.event_name] % self.get_context()
    
    @property
    def get_text(self):
        return self.html_events[self.event_name] % self.get_context()
