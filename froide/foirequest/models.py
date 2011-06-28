import random
from datetime import datetime, timedelta
import json

from django.db import models
from django.db.models.signals import pre_delete
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
from django.utils.http import urlquote
from django.core.mail import send_mail
from django.utils.safestring import mark_safe
from django.utils.html import escape

from publicbody.models import PublicBody, FoiLaw
from froide.helper.email_utils import make_address
from froide.helper.date_utils import convert_to_local
from froide.helper.text_utils import (replace_email_name,
        replace_email, remove_signature, remove_quote)
from foirequest.foi_mail import send_foi_mail

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

    def get_overdue(self):
        now = datetime.now()
        return self.get_query_set().filter(status="awaiting_response", due_date__lt=now)


class PublishedFoiRequestManager(CurrentSiteManager):
    def get_query_set(self):
        return super(PublishedFoiRequestManager,
                self).get_query_set().filter(public=True)

    def awaiting_response(self):
        return self.get_query_set().filter(
                    status="awaiting_response")

    def get_for_latest_feed(self):
        return self.get_query_set().order_by("-first_message")[:15]

    def successful(self):
        return self.get_query_set().filter(
                    models.Q(status="successful")|
                    models.Q(status="partially_successful"))

class FoiRequest(models.Model):
    ADMIN_SET_CHOICES = (
        ('awaiting_user_confirmation', _('Awaiting user confirmation'),
            _("The requester's email address is yet to be confirmed.")),
        ('publicbody_needed', _('Public Body needed'),
            _('This request still needs a Public Body.')),
        ('awaiting_publicbody_confirmation',
            _('Awaiting Public Body confirmation'),
            _('The Public Body of this request has been created by the user and still needs to be confirmed.')),
        ('overdue', _('Response overdue'),
            _('The request has not been answered in the legal time limit.')),
    )
    USER_SET_CHOICES = (
        ('awaiting_response', _('Awaiting response'),
                _('This request is still waiting for a response from the Public Body.')),
        ('awaiting_clarification',
                _('Awaiting clarification from Public Body'),
                _('A response was not satisfying to the requester and he requested more information.')),
        ('successful', _('Request Successful'),
            _('The request has been successul.')),
        ('partially_successful', _('Request partially successful'),
            _('The request has been partially successful (some information was provided, but not all)')),
        ('not_held', _('Information not held'),
            _('The Public Body stated that it does not possess the information.')),
        ('refused', _('Request refused'),
            _('The Public Body refuses to provide the information.')),
        # ('gone_postal', _('Gone Postal'), _('')),
        # ('escalation', _('Escalate Request'), _('')),
        # ('user_withdrawn', _('User withdrew request'), _('')),
    )

    if settings.FROIDE_CONFIG.get('payment_possible'):
        USER_SET_CHOICES += (('requires_payment',
                        _('Costs specified'),
                        _('The Public Body specified the costs for providing the information.')),
                # ('payment_refused', _('Payment refused'), _('')),
                # ('payment_accepted', _('Payment accepted'), _(''))
            )

    STATUS_CHOICES = [(x[0], x[1]) for x in ADMIN_SET_CHOICES + USER_SET_CHOICES]
    STATUS_CHOICES_DICT = dict([(x[0], (x[1], x[2])) for x in ADMIN_SET_CHOICES + USER_SET_CHOICES])

    VISIBILITY_CHOICES = (
        (0, _("Invisible")),
        (1, _("Visible to Requester")),
        (2, _("Public")),
    )

    # model fields
    title = models.CharField(_("Title"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    description = models.TextField(_("Description"), blank=True)
    resolution = models.TextField(_("Resolution Summary"),
            blank=True, null=True)
    public_body = models.ForeignKey(PublicBody, null=True, blank=True,
            on_delete=models.SET_NULL, verbose_name=_("Public Body"))

    public = models.BooleanField(_("published?"), default=True)

    status = models.CharField(_("Status"), max_length=25,
            choices=STATUS_CHOICES)
    visibility = models.SmallIntegerField(_("Visibility"), default=0,
            choices=VISIBILITY_CHOICES)
    
    user = models.ForeignKey(User, null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("User"))

    first_message = models.DateTimeField(_("Date of first message"),
            blank=True, null=True)
    last_message = models.DateTimeField(_("Date of last message"),
            blank=True, null=True)
    resolved_on = models.DateTimeField(_("Resolution date"),
            blank=True, null=True)
    due_date = models.DateTimeField(_("Due Date"),
            blank=True, null=True)
    
    secret_address = models.CharField(_("Secret address"), max_length=255,
            db_index=True, unique=True)
    secret = models.CharField(_("Secret"), blank=True, max_length=100)

    law = models.ForeignKey(FoiLaw, null=True, blank=True,
            on_delete=models.SET_NULL,
            verbose_name=_("Freedom of Information Law"))
    costs = models.FloatField(_("Cost of Information"), default=0.0)
    refusal_reason = models.CharField(_("Refusal reason"), max_length=255,
            blank=True)
    
    site = models.ForeignKey(Site, null=True,
            on_delete=models.SET_NULL, verbose_name=_("Site"))
    
    objects = FoiRequestManager()
    published = PublishedFoiRequestManager()

    class Meta:
        ordering = ('last_message',)
        get_latest_by = 'last_message'
        verbose_name = _('Freedom of Information Request')
        verbose_name_plural = _('Freedom of Information Requests')

    # Custom Signals
    message_sent = django.dispatch.Signal(providing_args=["message"])
    message_received = django.dispatch.Signal(providing_args=["message"])
    request_created = django.dispatch.Signal(providing_args=[])
    request_to_public_body = django.dispatch.Signal(providing_args=[])
    status_changed = django.dispatch.Signal(providing_args=["status", "data"])
    became_overdue = django.dispatch.Signal(providing_args=["status"])
    public_body_suggested = django.dispatch.Signal(providing_args=["suggestion"])
    made_public = django.dispatch.Signal(providing_args=[])


    def __unicode__(self):
        return _(u"Request '%s'") % self.title

    @property
    def messages(self):
        if not hasattr(self, "_messages"):
            self._messages = self.foimessage_set.select_related("sender_user",
                    "sender_public_body").order_by("timestamp")
        return self._messages

    @property
    def status_settable(self):
        return len(self.messages) > 1

    def get_absolute_url(self):
        return reverse('foirequest-show',
                kwargs={'slug': self.slug})

    def get_absolute_domain_url(self):
        return u"%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_description(self):
        return replace_email(self.description, _("<<email address>>"))

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

    def needs_public_body(self):
        return self.status == 'publicbody_needed'

    def awaits_response(self):
        return self.status == 'awaiting_response'

    def is_overdue(self):
        return self.due_date < datetime.now()

    def replyable(self):
        return not self.awaits_response()

    def public_date(self):
        if self.due_date:
            return self.due_date + timedelta(days=settings.FROIDE_CONFIG.get(
                'request_public_after_due_days', 14))
        return None

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
        else:
            self.refusal_reason = u""
        self.save()
        status = data.pop("status")
        self.status_changed.send(sender=self, status=status, data=data)

    def public_body_suggestions(self):
        if not hasattr(self, "_public_body_suggestion"):
            self._public_body_suggestion = \
                    PublicBodySuggestion.objects.filter(request=self) \
                        .select_related("public_body", "request")
        return self._public_body_suggestion

    def public_body_suggestions_form_klass(self):
        from foirequest.forms import get_public_body_suggestions_form_class
        return get_public_body_suggestions_form_class(
            self.public_body_suggestions())

    def public_body_suggestions_form(self):
        if not hasattr(self, "_public_body_suggestion_form"):
            self._public_body_suggestion_form = \
                    self.public_body_suggestions_form_klass()()
        return self._public_body_suggestion_form

    def make_public_body_suggestion_form(self):
        from foirequest.forms import MakePublicBodySuggestionForm
        return MakePublicBodySuggestionForm()

    def add_message_from_email(self, email, mail_string):
        message = FoiMessage(request=self)
        message.subject = email['subject']
        message.is_response = True
        message.sender_name = email['from'][0]
        message.sender_email = email['from'][1]
        message.sender_public_body = self.public_body
        message.timestamp = convert_to_local(*email['date'])
        message.recipient = self.secret_address
        # strip timezone, in case database can't handle it
        message.timestamp = message.timestamp.replace(tzinfo=None)
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

    def add_message(self, user, message=None, **kwargs):
        message_body = message
        message = FoiMessage(request=self)
        last_message = list(self.messages)[-1]
        message.subject = _("Re: %(subject)s"
                ) % {"subject": last_message.subject}
        message.is_response = False
        message.sender_user = user
        message.sender_name = user.get_profile().display_name()
        message.sender_email = self.secret_address
        message.recipient = last_message.sender_email
        message.timestamp = datetime.now()
        message.plaintext = message_body
        message.send()

    @classmethod
    def generate_secret_address(cls, user):
        possible_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        secret = "".join([random.choice(possible_chars) for i in range(10)])
        return "%s+%s@%s" % (user.username, secret, settings.FOI_EMAIL_DOMAIN)

    @property
    def readable_status(self):
        return FoiRequest.get_readable_status(self.status)

    @property
    def status_description(self):
        return FoiRequest.get_status_description(self.status)

    @classmethod
    def get_readable_status(cls, status):
        return cls.STATUS_CHOICES_DICT.get(status, (_("Unknown"), None))[0]

    @classmethod
    def get_status_description(cls, status):
        return cls.STATUS_CHOICES_DICT.get(status, (None, _("Unknown")))[1]

    @classmethod
    def from_request_form(cls, user, public_body_object, foi_law,
            **request_form):
        now = datetime.now()
        request = FoiRequest(title=request_form['subject'],
                public_body=public_body_object,
                user=user,
                description=request_form['body'],
                public=request_form['public'],
                site=Site.objects.get_current(),
                first_message=now,
                last_message=now)
        send_now = False
        if not user.is_active:
            request.status = 'awaiting_user_confirmation'
            request.visibility = 0
        else:
            request.determine_visibility()
            if public_body_object is None:
                request.status = 'publicbody_needed'
            elif not public_body_object.confirmed:
                request.status = 'awaiting_publicbody_confirmation'
            else:
                request.status = 'awaiting_response'
                send_now = True

        # ensure uniqueness of address
        while True:
            request.secret_address = cls.generate_secret_address(user)
            try:
                FoiRequest.objects.get(secret_address=request.secret_address)
            except FoiRequest.DoesNotExist:
                break

        #TODO: add right law
        request.law = foi_law

        # ensure slug is unique
        request.slug = slugify(request.title)
        count = 0
        postfix = ""
        while True:
            if count:
                postfix = "-%d" % count
            try:
                FoiRequest.objects.get(slug=request.slug + postfix)
            except FoiRequest.DoesNotExist:
                break
            count += 1
        request.slug += postfix

        if send_now:
            request.due_date = request.law.calculate_due_date()
        request.save()
        message = FoiMessage(request=request,
                sent=False,
                is_response=False,
                sender_user=user,
                sender_email=request.secret_address,
                sender_name=user.get_profile().display_name(),
                timestamp=now,
                subject=request.title)
        if public_body_object is not None:
            message.recipient = public_body_object.email
            cls.request_to_public_body.send(sender=request)
            message.plaintext = cls.construct_message_body(message,
                request_form['body'])
        else:
            message.recipient = ""
            message.plaintext = request_form['body']
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

    def determine_visibility(self):
        if self.public:
            self.visibility = 2
        else:
            self.visibility = 1

    def set_status_after_change(self):
        if not self.user.is_active:
            self.status = "awaiting_user_confirmation"
        else:
            self.determine_visibility()
            if self.public_body is None:
                self.status = 'publicbody_needed'
            elif not self.public_body.confirmed:
                self.status = 'awaiting_publicbody_confirmation'
            else:
                self.status = 'awaiting_response'
                return True
        return False

    def safe_send_first_message(self):
        messages = self.foimessage_set.all()
        if not len(messages) == 1:
            return None
        message = messages[0]
        if message.sent:
            return None
        message.send()
        return self

    @classmethod
    def confirmed_request(cls, user, request_id):
        try:
            request = FoiRequest.objects.get(pk=request_id)
        except FoiRequest.DoesNotExist:
            return None
        if not request.user == user:
            return None
        send_now = request.set_status_after_change()
        if send_now:
            request.due_date = request.law.calculate_due_date()
        request.save()
        if send_now:
            return request.safe_send_first_message()
        return None

    def confirmed_public_body(self):
        send_now = self.set_status_after_change()
        self.save()
        if send_now:
            return self.safe_send_first_message()
        return None

    def suggest_public_body(self, public_body, reason, user):
        try:
            PublicBodySuggestion.objects.get(public_body=public_body,
                    request=self)
        except PublicBodySuggestion.DoesNotExist:
            suggestion = self.publicbodysuggestion_set.create(
                    public_body=public_body,
                    reason=reason,
                    user=user)
            self.public_body_suggested.send(sender=self,
                    suggestion=suggestion)
            return suggestion
        else:
            return False


    def set_public_body(self, public_body, law):
        assert self.public_body == None
        assert self.status == "publicbody_needed"
        self.public_body = public_body
        self.law = law
        send_now = self.set_status_after_change()
        if send_now:
            self.due_date = self.law.calculate_due_date()
        self.save()
        self.request_to_public_body.send(sender=self)
        if send_now:
            messages = self.foimessage_set.all()
            assert len(messages) == 1
            message = messages[0]
            message.recipient = public_body.email
            message.plaintext = FoiRequest.construct_message_body(message,
                message.plaintext)
            assert message.sent == False
            message.send()  # saves message

    def make_public(self):
        self.public = True
        self.visibility = 2
        self.save()
        self.made_public.send(sender=self)

    def set_overdue(self):
        if not self.awaits_response():
            return None
        self.status = "overdue"
        self.save()
        self.became_overdue.send(sender=self)
        self.status_changed.send(sender=self, status=self.status, data={})

    

@receiver(FoiRequest.request_to_public_body,
        dispatch_uid="foirequest_increment_request_count")
def increment_request_count(sender, **kwargs):
    sender.public_body.number_of_requests += 1
    sender.public_body.save()

@receiver(pre_delete, sender=FoiRequest,
        dispatch_uid="foirequest_decrement_request_count")
def decrement_request_count(sender, instance=None, **kwargs):

    instance.public_body.number_of_requests -= 1
    if instance.public_body.number_of_requests < 0:
        instance.public_body.number_of_requests = 0
    instance.public_body.save()

@receiver(FoiRequest.message_received,
        dispatch_uid="notify_user_message_received")
def notify_user_message_received(sender, message=None, **kwargs):
    send_mail(_("You received a reply to your Freedom of Information Request"),
            render_to_string("foirequest/message_received_notification.txt",
                {"message": message, "request": sender,
                    "site_name": settings.SITE_NAME}),
            settings.DEFAULT_FROM_EMAIL,
            [sender.user.email])


@receiver(FoiRequest.public_body_suggested,
        dispatch_uid="notify_user_public_body_suggested")
def notify_user_public_body_suggested(sender, suggestion=None, **kwargs):
    if sender.user != suggestion.user:
        send_mail(_("Your request received a suggestion for a Public Body"),
                render_to_string("foirequest/public_body_suggestion_received.txt",
                    {"suggestion": suggestion, "request": sender,
                        "site_name": settings.SITE_NAME}),
                settings.DEFAULT_FROM_EMAIL,
                [sender.user.email])


class PublicBodySuggestion(models.Model):
    request = models.ForeignKey(FoiRequest,
            verbose_name=_("Freedom of Information Request"))
    public_body = models.ForeignKey(PublicBody,
            verbose_name=_("Public Body"))
    user = models.ForeignKey(User, null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("User"))
    timestamp = models.DateTimeField(_("Timestamp of Suggestion"),
            auto_now_add=True)
    reason = models.TextField(_("Reason this Public Body fits the request"),
            blank=True, default="")

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ('timestamp',)
        verbose_name = _('Public Body Suggestion')
        verbose_name_plural = _('Public Body Suggestions')


class FoiMessage(models.Model):
    request = models.ForeignKey(FoiRequest,
            verbose_name=_("Freedom of Information Request"))
    sent = models.BooleanField(_("has message been sent?"), default=True)
    is_response = models.BooleanField(_("Is this message a response?"),
            default=True)
    sender_user = models.ForeignKey(User, blank=True, null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("From User"))
    sender_email = models.CharField(_("From Email"),
            blank=True, max_length=255)
    sender_name = models.CharField(_("From Name"),
            blank=True, max_length=255)
    sender_public_body = models.ForeignKey(PublicBody, blank=True,
            null=True, on_delete=models.SET_NULL,
            verbose_name=_("From Public Body"))
    recipient = models.CharField(_("Recipient"), max_length=255,
            blank=True, null=True)
    timestamp = models.DateTimeField(_("Timestamp"), blank=True)
    subject = models.CharField(_("Subject"), blank=True, max_length=255)
    plaintext = models.TextField(_("plain text"), blank=True, null=True)
    html = models.TextField(_("HTML"), blank=True, null=True)
    original = models.TextField(_("Original"), blank=True)
    redacted = models.BooleanField(_("Was Redacted?"), default=False)

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ('timestamp',)
        # order_with_respect_to = 'request'
        verbose_name = _('Freedom of Information Message')
        verbose_name_plural = _('Freedom of Information Messages')

    GREETINGS = settings.POSSIBLE_GREETINGS
    CLOSINGS = settings.POSSIBLE_CLOSINGS

    @property
    def content(self):
        return self.plaintext

    def __unicode__(self):
        return _(u"Message in '%(request)s' at %(time)s"
                ) % {"request": self.request,
                    "time": self.timestamp}

    def get_html_id(self):
        return _("message-%(id)d") % {"id": self.id}

    def get_absolute_url(self):
        return "%s#%s" % (self.request.get_absolute_url(),
                self.get_html_id())

    def get_absolute_domain_url(self):
        return "%s#%s" % (self.request.get_absolute_domain_url(),
                self.get_html_id())


    @property
    def sender(self):
        if self.sender_user:
            return self.sender_user.get_profile().display_name
        if settings.FROIDE_CONFIG.get("public_body_officials_email_public",
                False):
            return make_address(self.sender_email, self.sender_name)
        if settings.FROIDE_CONFIG.get("public_body_officials_public",
                False) and self.sender_name:
            return self.sender_name
        else:
            return self.sender_public_body.name

    @property
    def attachments(self):
        if not hasattr(self, "_attachments"):
            self._attachments = list(self.foiattachment_set.all())
        return self._attachments

    def get_content(self):
        content = self.content
        # content = remove_quote(content,
        #        replacement=_(u"Quoted part removed"))
        if self.request.user:
            profile = self.request.user.get_profile()
            content = profile.apply_message_redaction(content)

        for greeting in self.GREETINGS:
            match = greeting.search(content)
            if match is not None and len(match.groups()):
                content = content.replace(match.group(1), _("<< Greeting >>"))

        for closing in self.CLOSINGS:
            match = closing.search(content)
            if match is not None:
                content = content[:match.end()]

        content = replace_email_name(content, _("<<name and email address>>"))
        content = replace_email(content, _("<<email address>>"))
        content = remove_signature(content)
        content = remove_quote(content)
        return content

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.sender_user and self.sender_public_body:
            raise ValidationError(
                    'Message may not be from user and public body')

    def send(self):
        if settings.FROIDE_DRYRUN:
            recp = self.recipient.replace("@", "+")
            self.recipient = "%s@%s" % (recp, settings.FROIDE_DRYRUN_DOMAIN)
        # Use send_foi_mail here
        from_addr = make_address(self.request.secret_address,
                self.request.user.get_full_name())
        send_foi_mail(self.subject, self.plaintext, from_addr,
                [self.recipient])
        self.sent = True
        self.save()
        FoiRequest.message_sent.send(sender=self.request, message=self)


@receiver(FoiRequest.message_sent,
        dispatch_uid="send_foimessage_sent_confirmation")
def send_foimessage_sent_confirmation(sender, message=None, **kwargs):
    if len(sender.messages) == 1:
        subject = _("Your Freedom of Information Request was sent")
        template = "foirequest/confirm_foi_request_sent.txt"
    else:
        subject = _("Your Message was sent")
        template = "foirequest/confirm_foi_message_sent.txt"
    send_mail(subject,
            render_to_string(template,
                {"request": sender, "message": message,
                    "site_name": settings.SITE_NAME}),
            settings.DEFAULT_FROM_EMAIL,
            [sender.user.email])


def upload_to(instance, filename):
    return "foi/%s/%s" % (instance.belongs_to.id, filename)


class FoiAttachment(models.Model):
    belongs_to = models.ForeignKey(FoiMessage, null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("Belongs to request"))
    name = models.CharField(_("Name"), max_length=255)
    file = models.FileField(_("File"), upload_to=upload_to)
    size = models.IntegerField(_("Size"), blank=True, null=True)
    filetype = models.CharField(_("File type"), blank=True, max_length=100)
    format = models.CharField(_("Format"), blank=True, max_length=100)
    
    class Meta:
        ordering = ('name',)
        # order_with_respect_to = 'belongs_to'
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')

    def __unicode__(self):
        return u"%s (%s) of %s" % (self.name, self.size, self.belongs_to)

    def can_preview(self):
        return True

    def get_preview_url(self):
        return "https://docs.google.com/viewer?url=%s%s" % (settings.SITE_URL,
                urlquote(self.file.url))

class FoiEventManager(models.Manager):
    def create_event(self, event_name, request, **context):
        assert event_name in FoiEvent.event_texts
        event = FoiEvent(request=request,
                public=request.visibility == 2,
                event_name=event_name)
        event.user = context.pop("user", None)
        event.public_body = context.pop("public_body", None)
        event.context_json = json.dumps(context)
        event.save()
        return event

    def get_for_homepage(self):
        return self.get_query_set().filter(public=True)

class FoiEvent(models.Model):
    request = models.ForeignKey(FoiRequest,
            verbose_name=_("Freedom of Information Request"))
    user = models.ForeignKey(User, null=True,
            on_delete=models.SET_NULL, blank=True,
            verbose_name=_("User"))
    public_body = models.ForeignKey(PublicBody, null=True,
            on_delete=models.SET_NULL, blank=True,
            verbose_name=_("Public Body"))
    public = models.BooleanField(_("Is Public?"), default=True)
    event_name = models.CharField(_("Event Name"), max_length=255)
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True)
    context_json = models.TextField(_("Context JSON"))

    objects = FoiEventManager()

    event_texts = {
        "public_body_suggested":
            _("%(user)s suggested %(public_body)s for the request '%(request)s'"),
        "reported_costs": _(
            u"%(user)s reported costs of %(amount)s for this request."),
        "message_received": _(
            u"Received an email from %(public_body)s."),
        "message_sent": _(
            u"%(user)s sent a message to %(public_body)s."),
        "status_changed": _(
            u"%(user)s set status to '%(status)s'."),
        "made_public": _(
            u"%(user)s made the request '%(request)s' public."),
        "request_refused": _(
            u"%(public_body)s refused to provide information on the grounds of %(reason)s.")
    }

    class Meta:
        ordering = ('timestamp',)
        verbose_name = _('Request Event')
        verbose_name_plural = _('Request Events')

    def __unicode__(self):
        return u"%s - %s" % (self.event_name, self.request)

    def get_html_id(self):
        # Translators: Hash part of Event URL
        return "%s-%d" % (_("event"), self.id)

    def get_absolute_url(self):
        return "%s#%s" % (self.request.get_absolute_url(),
                self.get_html_id())

    def get_context(self):
        context = getattr(self, "_context", None)
        if context is not None:
            return context
        context = json.loads(self.context_json)
        user = ""
        if self.user:
            user = self.user.get_profile().display_name()
        pb = ""
        if self.public_body:
            pb = self.public_body.name
        context.update({"user": user, "public_body": pb,
            "since": timesince(self.timestamp), "date": self.timestamp,
            "request": self.request.title})
        self._context = context
        return context

    def get_html_context(self):
        context = getattr(self, "_html_context", None)
        if context is not None:
            return context
        def link(url, title):
            return mark_safe('<a href="%s">%s</a>' % (url, escape(title)))
        context = self.get_context()
        if self.user:
            profile = self.user.get_profile()
            if not profile.private:
                context['user'] = link(profile.get_absolute_url(),
                        context['user'])
        if self.public_body:
            context['public_body'] = link(self.public_body.get_absolute_url(),
                    context['public_body'])
        context['request'] = link(self.request.get_absolute_url(),
                context['request'])
        self._html_context = context
        return context

    def as_text(self):
        return self.event_texts[self.event_name] % self.get_context()
    
    def as_html(self):
        return mark_safe(self.event_texts[self.event_name] % self.get_html_context())


@receiver(FoiRequest.message_sent, dispatch_uid="create_event_message_sent")
def create_event_message_sent(sender, **kwargs):
    FoiEvent.objects.create_event("message_sent", sender, user=sender.user,
            public_body=sender.public_body)


@receiver(FoiRequest.message_received,
        dispatch_uid="create_event_message_received")
def create_event_message_received(sender, **kwargs):
    FoiEvent.objects.create_event("message_received", sender,
            user=sender.user,
            public_body=sender.public_body)


@receiver(FoiRequest.status_changed,
        dispatch_uid="create_event_status_changed")
def create_event_status_changed(sender, **kwargs):
    status = kwargs['status']
    data = kwargs['data']
    if status == "requires_payment" and data['costs']:
        FoiEvent.objects.create_event("reported_costs", sender,
                user=sender.user,
                public_body=sender.public_body, amount=data['costs'])
    elif status == "refused" and data['refusal_reason']:
        FoiEvent.objects.create_event("request_refused", sender,
                user=sender.user,
                public_body=sender.public_body, reason=data['refusal_reason'])
    else:
        FoiEvent.objects.create_event("status_changed", sender, user=sender.user,
            public_body=sender.public_body,
            status=FoiRequest.get_readable_status(status))

@receiver(FoiRequest.made_public,
        dispatch_uid="create_event_made_public")
def create_event_made_public(sender, **kwargs):
    FoiEvent.objects.create_event("made_public", sender, user=sender.user,
            public_body=sender.public_body)

@receiver(FoiRequest.public_body_suggested,
        dispatch_uid="create_event_public_body_suggested")
def create_event_public_body_suggested(sender, suggestion=None, **kwargs):
    FoiEvent.objects.create_event("public_body_suggested", sender, user=suggestion.user,
            public_body=suggestion.public_body)

