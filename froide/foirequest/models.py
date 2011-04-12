import random
from datetime import datetime
import json

from django.db import models
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.core.urlresolvers import reverse
import django.dispatch
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.timesince import timesince

from mailer import send_mail

from publicbody.models import PublicBody, FoiLaw
from froide.helper.date_utils import convert_to_local

html2markdown = lambda x: x


class FoiRequestManager(CurrentSiteManager):
    def get_for_homepage(self, count=5):
        return self.get_query_set()[:count]

    def related_from_slug(self, slug):
        return self.get_query_set().filter(slug=slug).select_related()

    def get_by_secret_mail(self, mail):
        return self.get_query_set().get(secret_address=mail)


class FoiRequest(models.Model):
    title = models.CharField(_("Title"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    public_body = models.ForeignKey(PublicBody, null=True,
            on_delete=models.SET_NULL, verbose_name=_("Public Body"))

    published = models.BooleanField(_("published?"), default=True)

    _status = models.SmallIntegerField(default=0)
    _resolution = models.SmallIntegerField(default=0)
    _visibility = models.SmallIntegerField(default=0)
    
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
    
    site = models.ForeignKey(Site, null=True,
            on_delete=models.SET_NULL)
    
    objects = FoiRequestManager()

    class Meta:
        ordering = ('last_message',)
        get_latest_by = 'last_message'
        verbose_name = _('Freedom of Information Request')
        verbose_name_plural = _('Freedom of Information Requests')

    message_received = django.dispatch.Signal(providing_args=["message"])
    request_created = django.dispatch.Signal(providing_args=[])

    status_list = [
        'awaiting_response',
        'awaiting_clarification',
        'gone_postal',
        'not_held',
        'refused',
        'successful',
        'partially_successful',
        'internal_review',
        'error_message',
        'requires_admin',
        'user_withdrawn'
    ]

    status_message = {
        'awaiting_response': _('Awaiting Response'),
        'awaiting_clarification': _('Awaiting Clarification'),
        'gone_postal': _('Gone Postal'),
        'not_held': _('Information not held'),
        'refused': _('Refused'),
        'successful': _('Successful'),
        'partially_successful': _('Partially successful'),
        'internal_review': _('Internal Review'),
        'error_message': _('Error'),
        'requires_admin': _('Requires Administrator'),
        'user_withdrawn': _('Request was withdrawn')
    }

    def __unicode__(self):
        return u"Request '%s'" % self.title

    def get_absolute_url(self):
        return reverse('foirequest-show',
                kwargs={'slug': self.slug})

    def add_message_from_email(self, email, mail_string):
        message = FoiMessage(request=self)
        message.is_response = True
        message.sender_email = email['from'][1]
        message.sender_name = email['from'][0]
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
            att.file = attachment
            att.save()
        self.message_received.send(sender=self, message=message)

    @classmethod
    def generate_secret_address(cls, user):
        possible_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        secret = "".join([random.choice(possible_chars) for i in range(10)])
        return "%s+%s@%s" % (user.username, secret, settings.FOI_MAIL_DOMAIN)
                
    @classmethod
    def from_request_form(cls, user, public_body_object, **request_form):
        now = datetime.now()
        request = FoiRequest(title=request_form['subject'],
                public_body=public_body_object,
                user=user,
                site=Site.objects.get_current(),
                first_message=now,
                last_message=now)
        #TODO: ensure uniqueness of address
        request.secret_address = cls.generate_secret_address(user)
        #TODO: add right law
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
                recipient=public_body_object.email,
                subject=request.title)
        message.plaintext = cls.construct_message_body(message,
                request_form['body'])
        message.original = message.plaintext
        message.save()
        cls.request_created.send(sender=request)
        return request

    @classmethod
    def construct_message_body(cls, message, body):
        return render_to_string("foirequest/foi_request_mail.txt",
                {"message": message, "body": body}),

    @classmethod
    def confirmed_request(cls, user, request_id):
        try:
            request = FoiRequest.objects.get(pk=request_id)
        except FoiRequest.DoesNotExist:
            return None
        if not request.user == user:
            return None
        messages = request.foimessage_set.all()
        if not len(messages) == 1:
            return None
        message = messages[0]
        if message.sent:
            return None
        message.send()
        return request


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
    recipient = models.CharField(max_length=255)
    timestamp = models.DateTimeField(blank=True)
    subject = models.CharField(blank=True, max_length=255)
    plaintext = models.TextField(blank=True, null=True)
    html = models.TextField(blank=True, null=True)
    original = models.TextField(blank=True)
    redacted = models.BooleanField(default=False)

    _status = models.SmallIntegerField(null=True, default=None)
    _resolution = models.SmallIntegerField(null=True, default=None)
    _visibility = models.SmallIntegerField(default=1)

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ('timestamp',)
        # order_with_respect_to = 'request'
        verbose_name = _('Freedom of Information Message')
        verbose_name_plural = _('Freedom of Information Messages')

    @property
    def content(self):
        return self.plaintext or self.html

    def __unicode__(self):
        return u"Message in '%s' at %s" % (self.request,
                self.timestamp)

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


def upload_to(instance, filename):
    return "%s/foi/%s/%s" % (settings.MEDIA_ROOT, "/foi/",
            instance.belongs_to.id, filename)


class FoiAttachment(models.Model):
    belongs_to = models.ForeignKey(FoiMessage, null=True,
            on_delete=models.SET_NULL)
    name = models.CharField(max_length=255)
    file = models.FileField(storage=FileSystemStorage,
            upload_to=upload_to)
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
