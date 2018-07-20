from __future__ import unicode_literals

from datetime import timedelta
import json

from django.utils.six import string_types, text_type as str
from django.db import models
from django.db.models import Q, When, Case, Value
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ungettext_lazy
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.urls import reverse

import django.dispatch
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible

from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase

from froide.publicbody.models import PublicBody, FoiLaw, Jurisdiction
from froide.helper.text_utils import redact_plaintext

from .project import FoiProject


class FoiRequestManager(CurrentSiteManager):

    def get_send_foi_requests(self):
        return self.get_queryset().filter(
            is_foi=True,
            visibility__gt=FoiRequest.INVISIBLE
        )

    def get_by_secret_mail(self, mail):
        return self.get_queryset().get(secret_address=mail)

    def get_overdue(self):
        now = timezone.now()
        return self.get_queryset().filter(status="awaiting_response", due_date__lt=now)

    def get_to_be_overdue(self):
        yesterday = timezone.now() - timedelta(days=1)
        return self.get_overdue().filter(due_date__gt=yesterday)

    def get_asleep(self):
        six_months_ago = timezone.now() - timedelta(days=30 * 6)
        return self.get_queryset()\
            .filter(
                last_message__lt=six_months_ago
            ).filter(
                status='awaiting_response'
            )

    def get_to_be_asleep(self):
        return self.get_asleep().exclude(status='asleep')

    def get_unclassified(self):
        some_days_ago = timezone.now() - timedelta(days=4)
        return self.get_queryset().filter(status="awaiting_classification",
                last_message__lt=some_days_ago)

    def get_dashboard_requests(self, user, query=None):
        query_kwargs = {}
        if query is not None:
            query_kwargs = {'title__icontains': query}
        now = timezone.now()
        return self.get_queryset().filter(user=user, **query_kwargs).annotate(
            is_important=Case(
                When(Q(status="awaiting_classification") | (
                    Q(due_date__lt=now) & Q(status='awaiting_response')
                ), then=Value(True)),
                default=Value(False),
                output_field=models.BooleanField()
            )
        ).order_by('-is_important', '-last_message')

    def get_throttle_filter(self, user):
        return self.get_queryset().filter(user=user), 'first_message'


class PublishedFoiRequestManager(CurrentSiteManager):
    def get_queryset(self):
        qs = super(PublishedFoiRequestManager, self).get_queryset()
        return qs.filter(
            visibility=FoiRequest.VISIBLE_TO_PUBLIC, is_foi=True
        ).select_related("public_body", "jurisdiction")

    def by_last_update(self):
        return self.get_queryset().order_by('-last_message')

    def for_list_view(self):
        return self.by_last_update().filter(
            same_as__isnull=True,
        ).filter(
            models.Q(project__isnull=True) | models.Q(project_order=0)
        )

    def get_for_search_index(self):
        return self.get_queryset().filter(same_as__isnull=True)

    def get_resolution_count_by_public_body(self, obj):
        from ..filters import REVERSE_FILTER_DICT

        res = self.get_queryset().filter(
                status='resolved', public_body=obj
        ).values('resolution'
        ).annotate(
            models.Count('resolution')
        ).order_by('-resolution__count')

        return [{
            'resolution': x['resolution'],
            'url_slug': REVERSE_FILTER_DICT[x['resolution']][0],
            'name': REVERSE_FILTER_DICT[x['resolution']][2],
            'description': REVERSE_FILTER_DICT[x['resolution']][3],
            'count': x['resolution__count']
            } for x in res if x['resolution']]

    def successful(self):
        return self.by_last_update().filter(
                    models.Q(resolution="successful") |
                    models.Q(resolution="partially_successful")).order_by("-last_message")

    def unsuccessful(self):
        return self.by_last_update().filter(
                    models.Q(resolution="refused") |
                    models.Q(resolution="not_held")).order_by("-last_message")


class PublishedNotFoiRequestManager(PublishedFoiRequestManager):
    def get_queryset(self):
        return super(PublishedFoiRequestManager,
                self).get_queryset().filter(visibility=2, is_foi=False)\
                        .select_related("public_body", "jurisdiction")


class TaggedFoiRequest(TaggedItemBase):
    content_object = models.ForeignKey('FoiRequest', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('FoI Request Tag')
        verbose_name_plural = _('FoI Request Tags')


@python_2_unicode_compatible
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
            _('The request has been successful.'),
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

    INVISIBLE = 0
    VISIBLE_TO_REQUESTER = 1
    VISIBLE_TO_PUBLIC = 2

    VISIBILITY_CHOICES = (
        (INVISIBLE, _("Invisible")),
        (VISIBLE_TO_REQUESTER, _("Visible to Requester")),
        (VISIBLE_TO_PUBLIC, _("Public")),
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

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
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

    reference = models.CharField(_("Reference"), blank=True, max_length=255)

    same_as = models.ForeignKey('self', null=True, blank=True,
            on_delete=models.SET_NULL,
            verbose_name=_("Identical request"))
    same_as_count = models.IntegerField(_("Identical request count"), default=0)

    project = models.ForeignKey(FoiProject, null=True, blank=True,
            on_delete=models.SET_NULL, verbose_name=_('project'))
    project_order = models.IntegerField(null=True, blank=True)

    law = models.ForeignKey(FoiLaw, null=True, blank=True,
            on_delete=models.SET_NULL,
            verbose_name=_("Freedom of Information Law"))
    costs = models.FloatField(_("Cost of Information"), default=0.0)
    refusal_reason = models.CharField(_("Refusal reason"), max_length=1024,
            blank=True)
    checked = models.BooleanField(_("checked"), default=False)
    is_blocked = models.BooleanField(_("Blocked"), default=False)
    is_foi = models.BooleanField(_("is FoI request"), default=True)
    closed = models.BooleanField(_('is closed'), default=False)

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
        ordering = ('-last_message',)
        get_latest_by = 'last_message'
        verbose_name = _('Freedom of Information Request')
        verbose_name_plural = _('Freedom of Information Requests')
        permissions = (
            ("see_private", _("Can see private requests")),
            ("create_batch", _("Create batch requests")),
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

    def __str__(self):
        return _("Request '%s'") % self.title

    @property
    def same_as_set(self):
        return FoiRequest.objects.filter(same_as=self)

    @property
    def messages(self):
        if not hasattr(self, "_messages") or self._messages is None:
            self._messages = list(self.foimessage_set.select_related(
                "sender_user",
                "sender_public_body",
                "recipient_public_body").order_by("timestamp"))
        return self._messages

    def get_messages(self):
        self._messages = None
        return self.messages

    @property
    def status_representation(self):
        if self.due_date is not None:
            now = timezone.now()
            if self.status == 'awaiting_response' and now > self.due_date:
                return 'overdue'
        return self.status if self.status != 'resolved' else self.resolution

    @property
    def status_settable(self):
        return self.awaits_classification()

    @property
    def has_fee(self):
        return self.costs > 0

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
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_absolute_domain_short_url(self):
        return "%s%s" % (settings.SITE_URL, reverse('foirequest-shortlink',
                kwargs={'obj_id': self.id}))

    def get_auth_link(self):
        from ..auth import get_foirequest_auth_code

        return "%s%s" % (settings.SITE_URL,
            reverse('foirequest-auth',
                kwargs={"obj_id": self.id,
                    "code": get_foirequest_auth_code(self)
                }))

    def get_accessible_link(self):
        if self.visibility == self.VISIBLE_TO_REQUESTER:
            return self.get_auth_link()
        return self.get_absolute_domain_short_url()

    def is_public(self):
        return self.visibility == self.VISIBLE_TO_PUBLIC

    def get_redaction_regexes(self):
        user = self.user
        foimail_domain = settings.FOI_EMAIL_DOMAIN
        if not isinstance(foimail_domain, (list, tuple)):
            foimail_domain = [foimail_domain]
        email_regexes = [r'[\w\.\-]+@' + x for x in foimail_domain]
        FROIDE_CONFIG = settings.FROIDE_CONFIG
        user_regexes = []
        if user.private:
            user_regexes = [
                '%s %s' % (FROIDE_CONFIG['redact_salutation'], user.get_full_name()),
                '%s %s' % (FROIDE_CONFIG['redact_salutation'], user.last_name),
                user.get_full_name(),
                user.last_name,
                user.first_name
            ]
        all_regexes = email_regexes + user_regexes + user.address.splitlines()
        return json.dumps([a.strip() for a in all_regexes if a.strip()])

    def get_description(self):
        return redact_plaintext(self.description, is_response=False, user=self.user)

    def response_messages(self):
        return list(filter(lambda m: m.is_response, self.messages))

    def sent_messages(self):
        return list(filter(lambda m: m.is_response, self.messages))

    def reply_received(self):
        return len(self.response_messages()) > 0

    def message_needs_status(self):
        mes = list(filter(lambda m: m.status is None, self.response_messages()))
        if not mes:
            return None
        return mes[0]

    def status_is_final(self):
        return self.status == 'resolved'

    def is_visible(self):
        return self.visibility == self.VISIBLE_TO_PUBLIC

    def in_search_index(self):
        return (self.is_visible() and
            self.is_foi and self.same_as is None)

    def needs_public_body(self):
        return self.status == 'publicbody_needed'

    def awaits_response(self):
        return self.status == 'awaiting_response'

    def can_be_escalated(self):
        return not self.needs_public_body() and (
            self.is_overdue() or self.reply_received())

    def is_overdue(self):
        return self.was_overdue() and self.awaits_response()

    def was_overdue(self):
        if self.due_date:
            return self.due_date < timezone.now()
        return False

    def has_been_refused(self):
        return self.resolution == 'refused' or self.resolution == 'partially_successful'

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
            if isinstance(user, string_types):
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

    def possible_reply_addresses(self):
        addresses = {}
        for message in reversed(self.messages):
            if message.is_response:
                if message.sender_email and message.sender_email not in addresses:
                    addresses[message.sender_email] = message
        return addresses

    def get_set_tags_form(self):
        from ..forms import TagFoiRequestForm
        return TagFoiRequestForm(tags=self.tags.all())

    def get_status_form(self):
        from ..forms import FoiRequestStatusForm
        if self.status not in ('awaiting_response', 'resolved'):
            status = ''
        else:
            status = self.status
        return FoiRequestStatusForm(foirequest=self,
                    initial={"status": status,
                        'resolution': self.resolution,
                        "costs": self.costs,
                        "refusal_reason": self.refusal_reason})

    def public_body_suggestions_form(self):
        from ..forms import PublicBodySuggestionsForm
        return PublicBodySuggestionsForm(self)

    def make_public_body_suggestion_form(self):
        from ..forms import MakePublicBodySuggestionForm
        return MakePublicBodySuggestionForm()

    def get_concrete_law_form(self):
        from ..forms import ConcreteLawForm
        return ConcreteLawForm(foirequest=self)

    def get_postal_reply_form(self):
        from ..forms import get_postal_reply_form
        return get_postal_reply_form(foirequest=self)

    def get_postal_message_form(self):
        from ..forms import get_postal_message_form
        return get_postal_message_form(foirequest=self)

    def get_send_message_form(self):
        from ..forms import get_send_message_form
        return get_send_message_form(foirequest=self)

    def get_escalation_message_form(self):
        from ..forms import get_escalation_message_form
        return get_escalation_message_form(foirequest=self)

    def quote_last_message(self):
        return list(self.messages)[-1].get_quoted()

    @property
    def readable_status(self):
        return FoiRequest.get_readable_status(self.status_representation)

    @property
    def status_description(self):
        return FoiRequest.get_status_description(self.status_representation)

    @classmethod
    def get_readable_status(cls, status):
        return str(cls.STATUS_RESOLUTION_DICT.get(status, (_("Unknown"), None))[0])

    @classmethod
    def get_status_description(cls, status):
        return str(cls.STATUS_RESOLUTION_DICT.get(status, (None, _("Unknown")))[1])

    def determine_visibility(self):
        if self.public:
            self.visibility = self.VISIBLE_TO_PUBLIC
        else:
            self.visibility = self.VISIBLE_TO_REQUESTER

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
        from .suggestion import PublicBodySuggestion

        try:
            PublicBodySuggestion.objects.get(
                public_body=public_body,
                request=self
            )
        except PublicBodySuggestion.DoesNotExist:
            suggestion = self.publicbodysuggestion_set.create(
                    public_body=public_body,
                    reason=reason,
                    user=user)
            self.public_body_suggested.send(
                sender=self,
                suggestion=suggestion
            )
            return suggestion
        else:
            return False

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
        if self.user is None:
            return
        if not self.user.is_active:
            return
        if not self.user.email:
            return
        send_mail('{0} [#{1}]'.format(
                _("%(site_name)s: Please classify the reply to your request") % {
                    "site_name": settings.SITE_NAME
                },
                self.pk
        ),
            render_to_string("foirequest/emails/classification_reminder.txt", {
                "request": self,
                "go_url": self.user.get_autologin_url(self.get_absolute_short_url()),
                "site_name": settings.SITE_NAME
            }),
            settings.DEFAULT_FROM_EMAIL,
            [self.user.email]
        )

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
        for request in req_event_dict:
            req_event_dict[request].update({
                'go_url': user.get_autologin_url(
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
