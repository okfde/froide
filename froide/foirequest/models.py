import base64
import random
from datetime import timedelta
import json
import re

from django.db import models
from django.db.models import Q
from django.db import transaction, IntegrityError
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ungettext_lazy
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.core.urlresolvers import reverse
from django.core.files import File
import django.dispatch
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.timesince import timesince
from django.utils.http import urlquote
from django.core.mail import send_mail, mail_managers
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.crypto import salted_hmac, constant_time_compare
from django.utils import timezone

from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase

from froide.publicbody.models import PublicBody, FoiLaw, Jurisdiction
from froide.helper.email_utils import make_address
from froide.helper.text_utils import (replace_email_name,
        replace_email, remove_signature, remove_quote, strip_all_tags)

from .foi_mail import send_foi_mail


class FoiRequestManager(CurrentSiteManager):
    def get_for_homepage(self, count=5):
        return self.get_query_set().order_by("-last_message")[:count]

    def related_from_slug(self, slug):
        return self.get_query_set().filter(slug=slug).select_related()

    def get_by_secret_mail(self, mail):
        return self.get_query_set().get(secret_address=mail)

    def get_overdue(self):
        now = timezone.now()
        return self.get_query_set().filter(status="awaiting_response", due_date__lt=now)

    def get_to_be_overdue(self):
        yesterday = timezone.now() - timedelta(days=1)
        return self.get_overdue().filter(due_date__gt=yesterday)

    def get_asleep(self):
        six_months_ago = timezone.now() - timedelta(days=30 * 6)
        return self.get_query_set()\
            .filter(
                last_message__lt=six_months_ago
            ).filter(
                status='awaiting_response'
            )

    def get_to_be_asleep(self):
        return self.get_asleep().exclude(status='asleep')

    def get_unclassified(self):
        some_days_ago = timezone.now() - timedelta(days=4)
        return self.get_query_set().filter(status="awaiting_classification",
                last_message__lt=some_days_ago)

    def get_dashboard_requests(self, user):
        now = timezone.now()
        return self.get_query_set().filter(user=user).filter(
            Q(status="awaiting_classification") | (
                Q(due_date__lt=now) & Q(status='awaiting_response')
            )
        )


class PublishedFoiRequestManager(CurrentSiteManager):
    def get_query_set(self):
        return super(PublishedFoiRequestManager,
                self).get_query_set().filter(visibility=2, is_foi=True)\
                        .select_related("public_body", "jurisdiction")

    def awaiting_response(self):
        return self.get_query_set().filter(
                    status="awaiting_response")

    def by_last_update(self):
        return self.get_query_set().order_by('-last_message')

    def for_list_view(self):
        return self.by_last_update().filter(same_as__isnull=True)

    def get_for_homepage(self, count=5):
        return self.by_last_update().filter(
                models.Q(resolution='successful') |
                models.Q(resolution='partially_successful') |
                models.Q(resolution='refused'))[:count]

    def get_for_search_index(self):
        return self.get_query_set().filter(same_as__isnull=True)

    def successful(self):
        return self.by_last_update().filter(
                    models.Q(resolution="successful") |
                    models.Q(resolution="partially_successful")).order_by("-last_message")

    def unsuccessful(self):
        return self.by_last_update().filter(
                    models.Q(resolution="refused") |
                    models.Q(resolution="not_held")).order_by("-last_message")


class PublishedNotFoiRequestManager(PublishedFoiRequestManager):
    def get_query_set(self):
        return super(PublishedFoiRequestManager,
                self).get_query_set().filter(visibility=2, is_foi=False)\
                        .select_related("public_body", "jurisdiction")


class TaggedFoiRequest(TaggedItemBase):
    content_object = models.ForeignKey('FoiRequest')

    class Meta:
        verbose_name = _('FoI Request Tag')
        verbose_name_plural = _('FoI Request Tags')


class FoiRequest(models.Model):
    STATUS_CHOICES = (
        ('awaiting_user_confirmation',
            _('Awaiting user confirmation'),
            _("The requester's email address is yet to be confirmed."),
            False
        ),
        ('publicbody_needed',
            _('Public Body needed'),
            _('This request still needs a Public Body.'),
            False
        ),
        ('awaiting_publicbody_confirmation',
            _('Awaiting Public Body confirmation'),
            _('The Public Body of this request has been created by the user and still needs to be confirmed.'),
            False
        ),
        ('awaiting_response',
            _('Awaiting response'),
            _('This request is still waiting for a response from the Public Body.'),
            True
        ),
        ('awaiting_classification',
            _('Request awaits classification'),
            _('A message was received and the user needs to set a new status.'),
            False
        ),
        ('asleep',
            _('Request asleep'),
            _('The request is not resolved and has not been active for a while.'),
            False
        ),
        ('resolved',
            _('Request resolved'),
            _('The request is resolved.'),
            False
        ),
    )

    RESOLUTION_CHOICES = (
        ('successful',
            _('Request Successful'),
            _('The request has been successul.'),
            True
        ),
        ('partially_successful',
            _('Request partially successful'),
            _('The request has been partially successful (some information was provided, but not all)'),
            True),
        ('not_held',
            _('Information not held'),
            _('The Public Body stated that it does not possess the information.'),
            True,
        ),
        ('refused',
            _('Request refused'),
            _('The Public Body refuses to provide the information.'),
            True
        ),
        ('user_withdrew_costs',
            _('Request was withdrawn due to costs'),
            _('User withdrew the request due to the associated costs.'),
            True
        ),
        ('user_withdrew',
            _('Request was withdrawn'),
            _('User withdrew the request for other reasons.'),
            True
        ),
    )

    resolution_filter = lambda x: Q(resolution=x)
    status_filter = lambda x: Q(status=x)

    STATUS_URLS = [
        (_("successful"), resolution_filter, 'successful'),
        (_("partially-successful"), resolution_filter, 'partially_successful'),
        (_("refused"), resolution_filter, 'refused'),
        # (_("escalated"), 'status', 'escalated'),
        (_("withdrawn"), resolution_filter, 'user_withdrew'),
        (_("withdrawn-costs"), resolution_filter, 'user_withdrew_costs'),
        (_("publicbody-needed"), status_filter, 'publicbody_needed'),
        (_("awaiting-response"), status_filter, 'awaiting_response'),
        (_("overdue"), (lambda x:
            Q(due_date__lt=timezone.now()) & Q(status='awaiting_response')),
            'overdue'),
        (_("asleep"), status_filter, 'asleep'),
        (_("not-held"), resolution_filter, 'not_held'),
        (_("has-fee"), lambda x: Q(costs__gt=0), 'has_fee')
    ]

    _STATUS_URLS_DICT = None

    STATUS_FIELD_CHOICES = [(x[0], x[1]) for x in STATUS_CHOICES]
    RESOLUTION_FIELD_CHOICES = [(x[0], x[1]) for x in RESOLUTION_CHOICES]

    STATUS_RESOLUTION = STATUS_CHOICES + RESOLUTION_CHOICES

    STATUS_RESOLUTION_DICT = dict([(x[0], x[1:]) for x in STATUS_RESOLUTION])
    STATUS_RESOLUTION_DICT.update({
        'overdue': (
            _('Response overdue'),
            _('The request has not been answered in time.'),
            False
        ),
        'has_fee': (
            _('Fee charged'),
            _('This request is connected with a fee.'),
            False
        )
    })
    USER_STATUS_CHOICES = [(x[0], x[1]) for x in STATUS_RESOLUTION if x[3]]

    VISIBILITY_CHOICES = (
        (0, _("Invisible")),
        (1, _("Visible to Requester")),
        (2, _("Public")),
    )

    # model fields
    title = models.CharField(_("Title"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    description = models.TextField(_("Description"), blank=True)
    summary = models.TextField(_("Summary"), blank=True)

    public_body = models.ForeignKey(PublicBody, null=True, blank=True,
            on_delete=models.SET_NULL, verbose_name=_("Public Body"))

    status = models.CharField(_("Status"), max_length=50,
            choices=STATUS_FIELD_CHOICES)
    resolution = models.CharField(_("Resolution"),
        max_length=50, choices=RESOLUTION_FIELD_CHOICES, blank=True)

    public = models.BooleanField(_("published?"), default=True)
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

    same_as = models.ForeignKey('self', null=True, blank=True,
            on_delete=models.SET_NULL,
            verbose_name=_("Identical request"))
    same_as_count = models.IntegerField(_("Identical request count"), default=0)

    law = models.ForeignKey(FoiLaw, null=True, blank=True,
            on_delete=models.SET_NULL,
            verbose_name=_("Freedom of Information Law"))
    costs = models.FloatField(_("Cost of Information"), default=0.0)
    refusal_reason = models.CharField(_("Refusal reason"), max_length=1024,
            blank=True)
    checked = models.BooleanField(_("checked"), default=False)
    is_foi = models.BooleanField(_("is FoI request"), default=True)

    jurisdiction = models.ForeignKey(Jurisdiction, verbose_name=_('Jurisdiction'),
            null=True, on_delete=models.SET_NULL)

    site = models.ForeignKey(Site, null=True,
            on_delete=models.SET_NULL, verbose_name=_("Site"))

    non_filtered_objects = models.Manager()
    objects = FoiRequestManager()
    published = PublishedFoiRequestManager()
    published_not_foi = PublishedNotFoiRequestManager()
    tags = TaggableManager(through=TaggedFoiRequest, blank=True)

    class Meta:
        ordering = ('last_message',)
        get_latest_by = 'last_message'
        verbose_name = _('Freedom of Information Request')
        verbose_name_plural = _('Freedom of Information Requests')
        permissions = (
            ("see_private", _("Can see private requests")),
        )

    # Custom Signals
    message_sent = django.dispatch.Signal(providing_args=["message"])
    message_received = django.dispatch.Signal(providing_args=["message"])
    request_created = django.dispatch.Signal(providing_args=[])
    request_to_public_body = django.dispatch.Signal(providing_args=[])
    status_changed = django.dispatch.Signal(providing_args=["status", "data"])
    became_overdue = django.dispatch.Signal(providing_args=[])
    became_asleep = django.dispatch.Signal(providing_args=[])
    public_body_suggested = django.dispatch.Signal(providing_args=["suggestion"])
    set_concrete_law = django.dispatch.Signal(providing_args=['name'])
    made_public = django.dispatch.Signal(providing_args=[])
    add_postal_reply = django.dispatch.Signal(providing_args=[])
    escalated = django.dispatch.Signal(providing_args=[])

    def __unicode__(self):
        return _(u"Request '%s'") % self.title

    @classmethod
    def get_status_from_url(cls, status):
        if cls._STATUS_URLS_DICT is None:
            cls._STATUS_URLS_DICT = dict([
                (unicode(x[0]), x[1:]) for x in cls.STATUS_URLS])
        return cls._STATUS_URLS_DICT[status]

    @property
    def same_as_set(self):
        return FoiRequest.objects.filter(same_as=self)

    @property
    def messages(self):
        if not hasattr(self, "_messages") or \
                self._messages is None:
            self._messages = list(self.foimessage_set.select_related(
                "sender_user",
                "sender_user__profile",
                "sender_public_body",
                "recipient_public_body").order_by("timestamp"))
        return self._messages

    def get_messages(self):
        self._messages = None
        return self.messages

    @property
    def status_representation(self):
        now = timezone.now()
        if self.status == 'awaiting_response' and now > self.due_date:
            return 'overdue'
        return self.status if self.status != 'resolved' else self.resolution

    @property
    def status_settable(self):
        return self.awaits_classification()

    def identical_count(self):
        if self.same_as:
            return self.same_as.same_as_count
        return self.same_as_count

    def get_absolute_url(self):
        return reverse('foirequest-show',
                kwargs={'slug': self.slug})

    @property
    def url(self):
        return self.get_absolute_url()

    def get_absolute_short_url(self):
        return reverse('foirequest-shortlink',
                kwargs={'obj_id': self.id})

    def get_absolute_domain_url(self):
        return u"%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_absolute_domain_short_url(self):
        return u"%s%s" % (settings.SITE_URL, reverse('foirequest-shortlink',
                kwargs={'obj_id': self.id}))

    def get_auth_link(self):
        return u"%s%s" % (settings.SITE_URL,
            reverse('foirequest-auth',
                kwargs={"obj_id": self.id,
                    "code": self.get_auth_code()
                }))

    def get_accessible_link(self):
        if self.visibility == 1:
            return self.get_auth_link()
        return self.get_absolute_domain_short_url()

    def get_description(self):
        return replace_email(self.description, _("<<email address>>"))

    def response_messages(self):
        return filter(lambda m: m.is_response, self.messages)

    def reply_received(self):
        return len(self.response_messages()) > 0

    def message_needs_status(self):
        mes = filter(lambda m: m.status is None, self.response_messages())
        if not mes:
            return None
        return mes[0]

    def status_is_final(self):
        return self.status == 'resolved'

    def is_visible(self, user, pb_auth=None):
        if self.visibility == 0:
            return False
        if self.visibility == 2:
            return True
        if user and self.visibility == 1 and (
                user.is_authenticated() and
                self.user == user):
            return True
        if user and (user.is_superuser or user.has_perm('foirequest.see_private')):
            return True
        if self.visibility == 1 and pb_auth is not None:
            return self.check_auth_code(pb_auth)
        return False

    def needs_public_body(self):
        return self.status == 'publicbody_needed'

    def awaits_response(self):
        return self.status == 'awaiting_response' or self.status == 'overdue'

    def can_be_escalated(self):
        return not self.needs_public_body() and (
            self.is_overdue() or self.reply_received())

    def is_overdue(self):
        if self.due_date:
            return self.due_date < timezone.now()
        return False

    def has_been_refused(self):
        return self.status == 'refused' or self.status == 'escalated'

    def awaits_classification(self):
        return self.status == 'awaiting_classification'

    def set_awaits_classification(self):
        self.status = 'awaiting_classification'

    def follow_count(self):
        from froide.foirequestfollower.models import FoiRequestFollower
        return FoiRequestFollower.objects.filter(request=self).count()

    def followed_by(self, user):
        from froide.foirequestfollower.models import FoiRequestFollower
        try:
            if isinstance(user, basestring):
                return FoiRequestFollower.objects.get(request=self,
                        email=user, confirmed=True)
            else:
                return FoiRequestFollower.objects.get(request=self,
                        user=user)
        except FoiRequestFollower.DoesNotExist:
            return False

    def public_date(self):
        if self.due_date:
            return self.due_date + timedelta(days=settings.FROIDE_CONFIG.get(
                'request_public_after_due_days', 14))
        return None

    def get_set_tags_form(self):
        from .forms import TagFoiRequestForm
        return TagFoiRequestForm(self)

    def get_status_form(self):
        from .forms import FoiRequestStatusForm
        if self.status not in ('awaiting_response', 'resolved'):
            status = ''
        else:
            status = self.status
        return FoiRequestStatusForm(self,
                    initial={"status": status,
                        'resolution': self.resolution,
                        "costs": self.costs,
                        "refusal_reason": self.refusal_reason})

    def possible_reply_addresses(self):
        addresses = {}
        for message in reversed(self.messages):
            if message.is_response:
                if message.sender_email and not message.sender_email in addresses:
                    addresses[message.sender_email] = message
        return addresses

    def public_body_suggestions(self):
        if not hasattr(self, "_public_body_suggestion"):
            self._public_body_suggestion = \
                    PublicBodySuggestion.objects.filter(request=self) \
                        .select_related("public_body", "request")
        return self._public_body_suggestion

    def get_auth_code(self):
        return salted_hmac("FoiRequestPublicBodyAuth",
                '%s#%s' % (self.id, self.secret_address)).hexdigest()

    def check_auth_code(self, code):
        return constant_time_compare(code, self.get_auth_code())

    def public_body_suggestions_form(self):
        from .forms import PublicBodySuggestionsForm
        return PublicBodySuggestionsForm(self.public_body_suggestions())

    def make_public_body_suggestion_form(self):
        from .forms import MakePublicBodySuggestionForm
        return MakePublicBodySuggestionForm()

    def get_concrete_law_form(self):
        from .forms import ConcreteLawForm
        return ConcreteLawForm(self)

    def get_postal_reply_form(self):
        from .forms import PostalReplyForm
        return PostalReplyForm(initial={"date": timezone.now().date()})

    def quote_last_message(self):
        return list(self.messages)[-1].get_quoted()

    def find_public_body_for_email(self, email):
        if not email or not '@' in email:
            return self.public_body
        messages = list(reversed(self.messages))
        domain = email.split('@', 1)[1]
        for m in messages:
            if m.is_response:
                if m.sender_email == email:
                    return m.sender_public_body
                if ('@' in m.sender_email and
                        m.sender_email.split('@')[1] == domain):
                    return m.sender_public_body
        for m in messages:
            if not m.is_response:
                if m.recipient_email == email:
                    return m.recipient_public_body
                if ('@' in m.recipient_email and
                        m.recipient_email.split('@')[1] == domain):
                    return m.recipient_public_body
        return self.public_body

    def get_send_message_form(self):
        from .forms import SendMessageForm
        last_message = list(self.messages)[-1]
        subject = _("Re: %(subject)s"
                ) % {"subject": last_message.subject}
        if self.is_overdue() and self.awaits_response():
            message = render_to_string('foirequest/emails/overdue_reply.txt', {
                'foirequest': self
            })
        else:
            message = _("Dear Sir or Madam,\n\n...\n\nSincerely yours\n%(name)s\n")
            message = message % {'name': self.user.get_full_name()}
        return SendMessageForm(self,
                initial={"subject": subject,
                    "message": message})

    def get_escalation_message_form(self):
        from .forms import EscalationMessageForm
        subject = _('Complaint about request "%(title)s"'
                ) % {"title": self.title}
        return EscalationMessageForm(self,
                initial={
                    "subject": subject,
                    "message": render_to_string(
                            "foirequest/emails/mediation_message.txt",
                        {
                            "law": self.law.name,
                            "link": self.get_accessible_link(),
                            "name": self.user.get_full_name()
                        }
                    )})

    def add_message_from_email(self, email, mail_string):
        message = FoiMessage(request=self)
        message.subject = email['subject'][:250]
        message.is_response = True
        message.sender_name = email['from'][0]
        message.sender_email = email['from'][1]
        message.sender_public_body = self.find_public_body_for_email(message.sender_email)
        if message.sender_public_body == self.law.mediator:
            message.content_hidden = True
        message.timestamp = email['date']
        message.recipient_email = self.secret_address
        profile = self.user.get_profile()
        message.recipient = profile.display_name()
        message.plaintext = email['body']
        message.html = email['html']
        if not message.plaintext and message.html:
            message.plaintext = strip_all_tags(email['html'])
        message.subject_redacted = message.redact_subject()[:250]
        message.plaintext_redacted = message.redact_plaintext()
        message.save()
        self._messages = None
        self.status = 'awaiting_classification'
        self.last_message = message.timestamp
        self.save()
        has_pdf = False
        for i, attachment in enumerate(email['attachments']):
            att = FoiAttachment(belongs_to=message,
                    name=attachment.name,
                    size=attachment.size,
                    filetype=attachment.content_type)
            if att.name is None:
                att.name = _("attached_file_%d") % i
            att.name = profile.apply_message_redaction(att.name,
                {
                    'email': False,
                    'address': False,
                    # Translators: replacement for person name in filename
                    'name': unicode(_('NAME'))
                }
            )
            att.name = re.sub('[^\w\.\-]', '', att.name)
            att.name = att.name[:255]
            if att.name.endswith('pdf') or 'pdf' in att.filetype:
                has_pdf = True
            attachment._committed = False
            att.file = File(attachment)
            att.save()
        if (has_pdf and
                settings.FROIDE_CONFIG.get("mail_managers_on_pdf_attachment",
                    False)):
            mail_managers(_('Message contains PDF'),
                    self.get_absolute_domain_url())
        self.message_received.send(sender=self, message=message)

    def add_message(self, user, recipient_name, recipient_email,
            subject, message, recipient_pb=None, send_address=True):
        message_body = message
        message = FoiMessage(request=self)
        message.subject = subject
        message.subject_redacted = message.redact_subject()
        message.is_response = False
        message.sender_user = user
        message.sender_name = user.get_profile().display_name()
        message.sender_email = self.secret_address
        message.recipient_email = recipient_email
        message.recipient_public_body = recipient_pb
        message.recipient = recipient_name
        message.timestamp = timezone.now()
        message.plaintext = self.construct_standard_message_body(
            message_body,
            send_address=send_address)
        message.plaintext_redacted = message.redact_plaintext()
        message.send()
        return message

    def add_escalation_message(self, subject, message, send_address=False):
        message_body = message
        message = FoiMessage(request=self)
        message.subject = subject
        message.subject_redacted = message.redact_subject()
        message.is_response = False
        message.is_escalation = True
        message.sender_user = self.user
        message.sender_name = self.user.get_profile().display_name()
        message.sender_email = self.secret_address
        message.recipient_email = self.law.mediator.email
        message.recipient_public_body = self.law.mediator
        message.recipient = self.law.mediator.name
        message.timestamp = timezone.now()
        message.plaintext = self.construct_standard_message_body(message_body,
            send_address=send_address)
        message.plaintext_redacted = message.redact_plaintext()
        message.send()
        self.status = 'escalated'
        self.save()
        self.escalated.send(sender=self)

    @classmethod
    def generate_secret_address(cls, user):
        possible_chars = 'abcdefghkmnpqrstuvwxyz2345689'
        user_name = user.username.replace('_', '.')
        secret = "".join([random.choice(possible_chars) for i in range(10)])
        if getattr(settings, 'FOI_EMAIL_FUNC') and settings.FOI_EMAIL_FUNC:
            return settings.FOI_EMAIL_FUNC(user_name, secret)
        return "%s.%s@%s" % (user_name, secret, settings.FOI_EMAIL_DOMAIN)

    @classmethod
    def generate_unique_secret_address(cls, user):
        while True:
            address = cls.generate_secret_address(user)
            try:
                FoiRequest.objects.get(secret_address=address)
            except FoiRequest.DoesNotExist:
                break
        return address

    @property
    def readable_status(self):
        return FoiRequest.get_readable_status(self.status_representation)

    @property
    def status_description(self):
        return FoiRequest.get_status_description(self.status_representation)

    @classmethod
    def get_readable_status(cls, status):
        return unicode(cls.STATUS_RESOLUTION_DICT.get(status, (_("Unknown"), None))[0])

    @classmethod
    def get_status_description(cls, status):
        return unicode(cls.STATUS_RESOLUTION_DICT.get(status, (None, _("Unknown")))[1])

    @classmethod
    def from_request_form(cls, user, public_body_object, foi_law,
            form_data=None, post_data=None, **kwargs):
        now = timezone.now()
        request = FoiRequest(title=form_data['subject'],
                public_body=public_body_object,
                user=user,
                description=form_data['body'],
                public=form_data['public'],
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

        request.secret_address = cls.generate_unique_secret_address(user)
        request.law = foi_law
        if foi_law is not None:
            request.jurisdiction = foi_law.jurisdiction
        if send_now:
            request.due_date = request.law.calculate_due_date()

        # ensure slug is unique
        while True:
            request.slug = slugify(request.title)
            first_round = True
            count = 0
            postfix = ""
            with transaction.commit_manually():
                try:
                    while True:
                        if not first_round:
                            postfix = "-%d" % count
                        if not FoiRequest.objects.filter(slug=request.slug + postfix).exists():
                            break
                        if first_round:
                            first_round = False
                            count = FoiRequest.objects.filter(slug__startswith=request.slug).count()
                        else:
                            count += 1
                    request.slug += postfix
                    request.save()
                except IntegrityError:
                    transaction.rollback()
                else:
                    transaction.commit()
                    break

        message = FoiMessage(request=request,
                sent=False,
                is_response=False,
                sender_user=user,
                sender_email=request.secret_address,
                sender_name=user.get_profile().display_name(),
                timestamp=now,
                status="awaiting_response",
                subject=request.title)
        message.subject_redacted = message.redact_subject()
        send_address = True
        if request.law:
            send_address = not request.law.email_only
        message.plaintext = request.construct_message_body(form_data['body'],
                foi_law, post_data, send_address=send_address)
        message.plaintext_redacted = message.redact_plaintext()
        if public_body_object is not None:
            message.recipient_public_body = public_body_object
            message.recipient = public_body_object.name
            message.recipient_email = public_body_object.email
            cls.request_to_public_body.send(sender=request)
        else:
            message.recipient = ""
            message.recipient_email = ""
        message.original = ''
        message.save()
        cls.request_created.send(sender=request, reference=form_data.get('reference'))
        if send_now:
            message.send()
        return request

    def construct_message_body(self, text, foilaw, post_data, send_address=True):
        letter_start, letter_end = "", ""
        if foilaw:
            letter_start = foilaw.get_letter_start_text(post_data)
            letter_end = foilaw.get_letter_end_text(post_data)
        return render_to_string("foirequest/emails/foi_request_mail.txt",
                {"request": self,
                "letter_start": letter_start,
                "letter_end": letter_end,
                "body": text,
                "send_address": send_address
            })

    def construct_standard_message_body(self, text, send_address=True):
        return render_to_string("foirequest/emails/mail_with_userinfo.txt",
                {"request": self, "body": text, 'send_address': send_address})

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
        assert self.public_body is None
        assert self.status == "publicbody_needed"
        self.public_body = public_body
        self.law = law
        self.jurisdiction = public_body.jurisdiction
        send_now = self.set_status_after_change()
        if send_now:
            self.due_date = self.law.calculate_due_date()
        self.save()
        self.request_to_public_body.send(sender=self)
        if self.law:
            send_address = not self.law.email_only
        if send_now:
            messages = self.foimessage_set.all()
            assert len(messages) == 1
            message = messages[0]
            message.recipient_public_body = public_body
            message.recipient = public_body.name
            message.recipient_email = public_body.email
            message.plaintext = self.construct_message_body(
                self.description,
                self.law, {}, send_address=send_address)
            message.plaintext_redacted = message.redact_plaintext()
            assert not message.sent
            message.send()  # saves message

    def make_public(self):
        self.public = True
        self.visibility = 2
        self.save()
        self.made_public.send(sender=self)

    def set_overdue(self):
        self.became_overdue.send(sender=self)

    def set_asleep(self):
        self.status = "asleep"
        self.save()
        self.became_asleep.send(sender=self)

    def send_classification_reminder(self):
        if not self.user.is_active:
            return
        if not self.user.email:
            return
        send_mail(_("%(site_name)s: Please classify the reply to your request")
                    % {"site_name": settings.SITE_NAME},
                render_to_string("foirequest/emails/classification_reminder.txt",
                    {"request": self,
                        "go_url": self.user.get_profile().get_autologin_url(self.get_absolute_short_url()),
                        "site_name": settings.SITE_NAME}),
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email])

    @classmethod
    def send_update(cls, req_event_dict, user=None):
        if user is None:
            return
        count = len(req_event_dict)
        subject = ungettext_lazy(
            "%(site_name)s: Update on one of your request",
            "%(site_name)s: Update on %(count)s of your requests",
            count) % {
                'site_name': settings.SITE_NAME,
                'count': count
            }

        # Add additional info to template context
        user_profile = user.get_profile()
        for request in req_event_dict:
            req_event_dict[request].update({
                'go_url': user_profile.get_autologin_url(
                    request.get_absolute_short_url()
                )
            })

        send_mail(subject,
            render_to_string("foirequest/emails/request_update.txt",
                {
                    "user": user,
                    "count": count,
                    "req_event_dict": req_event_dict,
                    "site_name": settings.SITE_NAME
                }
            ),
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )

    def days_to_resolution(self):
        final = None
        resolutions = dict(self.RESOLUTION_FIELD_CHOICES)
        for mes in self.response_messages():
            if (mes.status == 'resolved' or
                        mes.status in resolutions):
                final = mes.timestamp
                break
        if final is None:
            return None
        return (mes.timestamp - self.first_message).days


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
    is_postal = models.BooleanField(_("Postal?"),
            default=False)
    is_escalation = models.BooleanField(_("Escalation?"),
            default=False)
    content_hidden = models.BooleanField(_("Content hidden?"),
            default=False)
    sender_user = models.ForeignKey(User, blank=True, null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("From User"))
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

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ('timestamp',)
        # order_with_respect_to = 'request'
        verbose_name = _('Freedom of Information Message')
        verbose_name_plural = _('Freedom of Information Messages')

    @property
    def content(self):
        return self.plaintext

    def __unicode__(self):
        return _(u"Message in '%(request)s' at %(time)s"
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

    def get_absolute_domain_url(self):
        return "%s#%s" % (self.request.get_absolute_domain_url(),
                self.get_html_id())

    def get_public_body_sender_form(self):
        from froide.foirequest.forms import MessagePublicBodySenderForm
        return MessagePublicBodySenderForm(self)

    def get_recipient(self):
        if self.recipient_public_body:
            return mark_safe('<a href="%(url)s">%(name)s</a>' % {
                "url": self.recipient_public_body.get_absolute_url(),
                "name": escape(self.recipient_public_body.name)})
        else:
            return self.recipient

    def get_quoted(self):
        return "\n".join([">%s" % l for l in self.plaintext.splitlines()])

    def needs_status_input(self):
        return self.request.message_needs_status() == self

    @property
    def sender(self):
        if self.sender_user:
            return self.sender_user.get_profile().display_name()
        if settings.FROIDE_CONFIG.get("public_body_officials_email_public",
                False):
            return make_address(self.sender_email, self.sender_name)
        if settings.FROIDE_CONFIG.get("public_body_officials_public",
                False) and self.sender_name:
            return self.sender_name
        else:
            return self.sender_public_body.name

    @property
    def real_sender(self):
        if self.sender_user:
            return self.sender_user.get_profile().display_name()
        if settings.FROIDE_CONFIG.get("public_body_officials_email_public",
                False):
            return make_address(self.sender_email, self.sender_name)
        if self.sender_name:
            return self.sender_name
        else:
            return self.sender_public_body.name

    @property
    def reply_address_entry(self):
        email = self.sender_email
        if email:
            return u'%s@... (%s)' % (email.split('@')[0], self.real_sender)
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
        # content = remove_quote(content,
        #        replacement=_(u"Quoted part removed"))
        if self.request.user:
            profile = self.request.user.get_profile()
            content = profile.apply_message_redaction(content)

        content = replace_email_name(content, _("<<name and email address>>"))
        content = replace_email(content, _("<<email address>>"))
        return content

    def get_content(self, user=None):
        if self.plaintext_redacted is None:
            self.plaintext_redacted = self.redact_plaintext()
            self.save()
        return self.plaintext_redacted

    def redact_plaintext(self):
        content = self.plaintext
        # content = remove_quote(content,
        #        replacement=_(u"Quoted part removed"))
        if self.request.user:
            profile = self.request.user.get_profile()
            content = profile.apply_message_redaction(content)

        content = replace_email_name(content, _("<<name and email address>>"))
        content = replace_email(content, _("<<email address>>"))
        content = remove_signature(content)
        content = remove_quote(content)
        return content

    def get_real_content(self):
        content = self.content
        content = replace_email(content, _("<<email address>>"))
        content = remove_quote(content)
        return content

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.sender_user and self.sender_public_body:
            raise ValidationError(
                    'Message may not be from user and public body')

    def get_postal_attachment_form(self):
        from froide.foirequest.forms import PostalAttachmentForm
        return PostalAttachmentForm()

    def send(self, notify=True):
        if settings.FROIDE_CONFIG['dryrun']:
            recp = self.recipient_email.replace("@", "+")
            self.recipient_email = "%s@%s" % (recp, settings.FROIDE_CONFIG['dryrun_domain'])
        # Use send_foi_mail here
        from_addr = make_address(self.request.secret_address,
                self.request.user.get_full_name())
        send_foi_mail(self.subject, self.plaintext, from_addr,
                [self.recipient_email])
        self.sent = True
        self.save()
        self.request._messages = None
        if notify:
            FoiRequest.message_sent.send(sender=self.request, message=self)


def upload_to(instance, filename):
    return "%s/%s/%s" % (settings.FOI_MEDIA_PATH, instance.belongs_to.id, instance.name)


class FoiAttachment(models.Model):
    belongs_to = models.ForeignKey(FoiMessage, null=True,
            verbose_name=_("Belongs to request"))
    name = models.CharField(_("Name"), max_length=255)
    file = models.FileField(_("File"), upload_to=upload_to, max_length=255)
    size = models.IntegerField(_("Size"), blank=True, null=True)
    filetype = models.CharField(_("File type"), blank=True, max_length=100)
    format = models.CharField(_("Format"), blank=True, max_length=100)
    can_approve = models.BooleanField(_("User can approve"), default=True)
    approved = models.BooleanField(_("Approved"), default=False)
    redacted = models.ForeignKey('self', verbose_name=_("Redacted Version"),
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='unredacted_set')
    is_redacted = models.BooleanField(_("Is redacted"), default=False)
    converted = models.ForeignKey('self', verbose_name=_("Converted Version"),
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='original_set')
    is_converted = models.BooleanField(_("Is redacted"), default=False)

    CONVERTABLE_FILETYPES = (
        'application/msword',
        'application/vnd.msword',
        '.doc',
        '.docx',
    )

    PREVIEWABLE_FILETYPES = (
        'application/msexcel',
        'application/vnd.ms-excel',
        'application/msword',
        'application/vnd.msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/pdf',
        'application/x-pdf',
        'pdf/application',
        'application/acrobat',
        'applications/vnd.pdf',
        'text/pdf',
        'text/x-pdf'
    )

    POSTAL_CONTENT_TYPES = PREVIEWABLE_FILETYPES + (
        "image/png",
        "image/jpeg",
        "image/jpg",
        "application/text-plain:formatted",
        "text/plain"
    )

    class Meta:
        ordering = ('name',)
        # order_with_respect_to = 'belongs_to'
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')

    def __unicode__(self):
        return u"%s (%s) of %s" % (self.name, self.size, self.belongs_to)

    def index_content(self):
        return "\n".join((self.name,))

    def has_public_access(self):
        if self.belongs_to:
            return self.belongs_to.request.visibility == 2 and self.approved
        return False

    def can_preview(self):
        return self.has_public_access() and self.filetype in self.PREVIEWABLE_FILETYPES

    def get_preview_url(self):
        return "https://docs.google.com/viewer?url=%s%s" % (
            settings.SITE_URL,
                urlquote(self.get_absolute_url()))

    def get_html_id(self):
        return _("attachment-%(id)d") % {"id": self.id}

    def get_internal_url(self):
        return settings.MEDIA_URL + self.file.name

    def get_anchor_url(self):
        if self.belongs_to:
            return '%s#%s' % (self.belongs_to.request.get_absolute_url(),
                self.get_html_id())
        return '#' + self.get_html_id()

    def get_absolute_url(self):
        if settings.USE_X_ACCEL_REDIRECT:
            return reverse('foirequest-auth_message_attachment',
                kwargs={
                    'message_id': self.belongs_to_id,
                    'attachment_name': self.name
                })
        else:
            return self.file.url

    def get_absolute_domain_url(self):
        return u"%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def is_visible(self, user, foirequest):
        if self.approved:
            return True
        if user and (
                user.is_authenticated() and
                foirequest.user == user):
            return True
        if user and (user.is_superuser or user.has_perm('foirequest.see_private')):
            return True
        return False

    def admin_link_message(self):
        return '<a href="%s">%s</a>' % (
            reverse('admin:foirequest_foimessage_change',
                args=(self.belongs_to_id,)), _('See FoiMessage'))
    admin_link_message.allow_tags = True


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
        return self.get_query_set().filter(public=True)\
                .select_related("user", "user__profile", "public_body",
                        "request")


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
    timestamp = models.DateTimeField(_("Timestamp"))
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
        "request_redirected": _(
            u"Request was redirected to %(public_body)s and due date has been reset."),
        "status_changed": _(
            u"%(user)s set status to '%(status)s'."),
        "made_public": _(
            u"%(user)s made the request '%(request)s' public."),
        "request_refused": _(
            u"%(public_body)s refused to provide information on the grounds of %(reason)s."),
        "partially_successful": _(
            u"%(public_body)s answered partially, but denied access to all information on the grounds of %(reason)s."),
        "became_overdue": _(
            u"This request became overdue"),
        "set_concrete_law": _(
            u"%(user)s set '%(name)s' as the information law for the request %(request)s."),
        "add_postal_reply": _(
            u"%(user)s added a reply that was received via snail mail."),
        "escalated": _(
            u"%(user)s filed a complaint to the %(public_body)s about the handling of this request %(request)s."),
        "deadline_extended": _(
            u"The deadline of request %(request)s has been extended.")
    }

    class Meta:
        ordering = ('-timestamp',)
        verbose_name = _('Request Event')
        verbose_name_plural = _('Request Events')

    def __unicode__(self):
        return u"%s - %s" % (self.event_name, self.request)

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.timestamp = timezone.now()
        super(FoiEvent, self).save(*args, **kwargs)

    def get_html_id(self):
        # Translators: Hash part of Event URL
        return u"%s-%d" % (unicode(_("event")), self.id)

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
        context.update({
            "user": user, "public_body": pb,
            "since": timesince(self.timestamp),
            "date": self.timestamp,
            "request": self.request.title
        })
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


class DeferredMessage(models.Model):
    recipient = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    request = models.ForeignKey(FoiRequest, null=True, blank=True)
    mail = models.TextField(blank=True)

    class Meta:
        ordering = ('timestamp',)
        get_latest_by = 'timestamp'
        verbose_name = _('Undelivered Message')
        verbose_name_plural = _('Undelivered Messages')

    def __unicode__(self):
        return _(u"Undelievered Message to %(recipient)s (%(request)s)") % {
            'recipient': self.recipient,
            'request': self.request
        }

    def redeliver(self, request):
        from .tasks import process_mail

        self.request = request
        self.save()
        mail = base64.b64decode(self.mail)
        mail = mail.replace(self.recipient, self.request.secret_address)
        process_mail.delay(mail.encode('utf-8'))


# Import Signals here so models are available
import froide.foirequest.signals  # noqa
froide.foirequest.signals
