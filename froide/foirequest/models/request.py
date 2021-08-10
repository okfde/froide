from collections import namedtuple
from datetime import timedelta
import json
import re

from django.db import models
from django.db.models import Q, When, Case, Value
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.urls import reverse
from django.utils.crypto import get_random_string

import django.dispatch
from django.utils import timezone

from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase

from froide.publicbody.models import PublicBody, FoiLaw, Jurisdiction
from froide.campaign.models import Campaign
from froide.team.models import Team
from froide.helper.text_utils import redact_plaintext

from .project import FoiProject


MODERATOR_CLASSIFICATION_OFFSET = timedelta(days=14)


class FoiRequestManager(CurrentSiteManager):

    def get_send_foi_requests(self):
        return self.get_queryset().filter(
            is_foi=True,
            visibility__gt=FoiRequest.VISIBILITY.INVISIBLE
        )

    def get_by_secret_mail(self, mail):
        return self.get_queryset().get(secret_address=mail)

    def get_overdue(self):
        now = timezone.now()
        return self.get_queryset().filter(
            status=Status.AWAITING_RESPONSE, due_date__lt=now
        )

    def get_to_be_overdue(self):
        yesterday = timezone.now() - timedelta(days=1)
        return self.get_overdue().filter(due_date__gt=yesterday)

    def get_asleep(self):
        six_months_ago = timezone.now() - timedelta(days=30 * 6)
        return self.get_queryset()\
            .filter(
                last_message__lt=six_months_ago
            ).filter(
                status=Status.AWAITING_RESPONSE
            )

    def get_to_be_asleep(self):
        return self.get_asleep().exclude(status=Status.ASLEEP)

    def get_unclassified(self, offset=None):
        if offset is None:
            offset = timedelta(days=4)
        ago = timezone.now() - offset
        return self.get_queryset().filter(
            status=Status.AWAITING_CLASSIFICATION,
            is_foi=True,
            last_message__lt=ago
        )

    def get_unclassified_for_moderation(self):
        return self.get_unclassified(offset=MODERATOR_CLASSIFICATION_OFFSET).filter(
            visibility=Visibility.VISIBLE_TO_PUBLIC
        )

    def get_dashboard_requests(self, user, query=None):
        query_kwargs = {}
        if query is not None:
            query_kwargs = {'title__icontains': query}
        now = timezone.now()
        return self.get_queryset().filter(user=user, **query_kwargs).annotate(
            is_important=Case(
                When(Q(status=Status.AWAITING_CLASSIFICATION) | (
                    Q(due_date__lt=now) & Q(status=Status.AWAITING_RESPONSE)
                ), then=Value(True)),
                default=Value(False),
                output_field=models.BooleanField()
            )
        ).order_by('-is_important', '-last_message')

    def get_throttle_filter(self, qs, user, extra_filters=None):
        qs = qs.filter(user=user)
        return qs, 'first_message'

    def delete_private_requests(self, user):
        if not user:
            return
        qs = self.get_queryset().filter(
            user=user
        ).filter(
            Q(visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER) |
            Q(visibility=FoiRequest.VISIBILITY.INVISIBLE)
        )
        for req in qs:
            # Trigger signals
            req.delete()


class PublishedFoiRequestManager(CurrentSiteManager):
    def get_queryset(self):
        qs = super(PublishedFoiRequestManager, self).get_queryset()
        return qs.filter(
            visibility=FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC, is_foi=True
        ).select_related("public_body", "jurisdiction")

    def by_last_update(self):
        return self.get_queryset().order_by('-last_message')

    def for_list_view(self):
        return self.by_last_update().filter(
            same_as__isnull=True,
        ).filter(
            models.Q(project__isnull=True) | models.Q(project_order=0)
        )

    def get_resolution_count_by_public_body(self, obj):
        from ..filters import REVERSE_FILTER_DICT

        res = self.get_queryset().filter(
                status=Status.RESOLVED, public_body=obj
        ).values('resolution'
        ).annotate(
            models.Count('resolution')
        ).order_by('-resolution__count')

        return [{
            'resolution': x['resolution'],
            'url_slug': REVERSE_FILTER_DICT[x['resolution']].slug,
            'name': REVERSE_FILTER_DICT[x['resolution']].label,
            'description': REVERSE_FILTER_DICT[x['resolution']].description,
            'count': x['resolution__count']
            } for x in res if x['resolution']]

    def successful(self):
        return self.by_last_update().filter(
                    models.Q(resolution=Resolution.SUCCESSFUL) |
                    models.Q(resolution=Resolution.PARTIALLY_SUCCESSFUL)).order_by("-last_message")

    def unsuccessful(self):
        return self.by_last_update().filter(
                    models.Q(resolution=Resolution.REFUSED) |
                    models.Q(resolution=Resolution.NOT_HELD)).order_by("-last_message")


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


class Status(models.TextChoices):
    AWAITING_USER_CONFIRMATION = "awaiting_user_confirmation", _(
        'Awaiting user confirmation')
    PUBLICBODY_NEEDED = 'publicbody_needed', _('Public Body needed')
    AWAITING_PUBLICBODY_CONFIRMATION = 'awaiting_publicbody_confirmation', _(
        'Awaiting Public Body confirmation')
    AWAITING_RESPONSE = 'awaiting_response', _('Awaiting response')
    AWAITING_CLASSIFICATION = 'awaiting_classification', _(
        'Request awaits classification')
    ASLEEP = 'asleep', _('Request asleep')
    RESOLVED = 'resolved', _('Request resolved')


class Resolution(models.TextChoices):
    SUCCESSFUL = 'successful', _('Request Successful')
    PARTIALLY_SUCCESSFUL = 'partially_successful', _(
        'Request partially successful')
    NOT_HELD = 'not_held', _('Information not held')
    REFUSED = 'refused', _('Request refused')
    USER_WITHDREW_COSTS = 'user_withdrew_costs', _(
        'Request was withdrawn due to costs')
    USER_WITHDREW = 'user_withdrew', _('Request was withdrawn')


class FilterStatus(models.TextChoices):
    OVERDUE = 'overdue', _('Response overdue')


StatusResolutionDetail = namedtuple('StatusResolutionDetail',
    'label description'
)

UNKNOWN_STATUS = StatusResolutionDetail(_('Unknown'), _('Unknown'))

STATUS_RESOLUTION_DESCRIPTIONS = [
    (Status.AWAITING_USER_CONFIRMATION,
        _("The requester's email address is yet to be confirmed.")),
    (Status.PUBLICBODY_NEEDED,
        _('This request still needs a Public Body.')),
    (Status.AWAITING_PUBLICBODY_CONFIRMATION,
        _('The Public Body of this request has been created by the user and '
          'still needs to be confirmed.')),
    (Status.AWAITING_RESPONSE,
        _('This request is still waiting for a response from the Public Body.'
        )),
    (Status.AWAITING_CLASSIFICATION,
        _('A message was received and the user needs to set a new status.')),
    (Status.ASLEEP,
        _('The request is not resolved and has not been active for a while.')),
    (Status.RESOLVED,
        _('The request is resolved.')),
    (Resolution.SUCCESSFUL,
        _('The request has been successful.')),
    (Resolution.PARTIALLY_SUCCESSFUL,
        _('The request has been partially successful (some information was '
          'provided, but not all)')),
    (Resolution.REFUSED,
        _('The Public Body refuses to provide the information.')),
    (Resolution.USER_WITHDREW_COSTS,
        _('User withdrew the request due to the associated costs.')),
    (Resolution.USER_WITHDREW,
        _('User withdrew the request for other reasons.')),
    (Resolution.NOT_HELD,
        _('The information does not exist at the public body.')),
    (FilterStatus.OVERDUE,
        _('The request has not been answered in time.'))
]

STATUS_RESOLUTION_DICT = {
    str(x[0]): StatusResolutionDetail(
        label=x[0].label,
        description=x[1]
    )
    for x in STATUS_RESOLUTION_DESCRIPTIONS
}


class Visibility(models.IntegerChoices):
    INVISIBLE = 0, _("Invisible")
    VISIBLE_TO_REQUESTER = 1, _("Visible to requester")
    VISIBLE_TO_PUBLIC = 2, _("Visible to public")


class FoiRequest(models.Model):
    STATUS = Status
    RESOLUTION = Resolution
    FILTER_STATUS = FilterStatus
    VISIBILITY = Visibility

    STATUS_RESOLUTION_DICT = STATUS_RESOLUTION_DICT

    # model fields
    title = models.CharField(_("Title"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    description = models.TextField(_("Description"), blank=True)
    summary = models.TextField(_("Summary"), blank=True)

    public_body = models.ForeignKey(PublicBody, null=True, blank=True,
            on_delete=models.SET_NULL, verbose_name=_("Public Body"))

    status = models.CharField(
        _("Status"), max_length=50, choices=Status.choices
    )
    resolution = models.CharField(
        _("Resolution"), max_length=50, choices=Resolution.choices,
        blank=True
    )

    public = models.BooleanField(_("published?"), default=True)
    visibility = models.SmallIntegerField(
        _("Visibility"), default=Visibility.INVISIBLE,
        choices=Visibility.choices
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
            on_delete=models.SET_NULL,
            verbose_name=_("User"))
    team = models.ForeignKey(Team, null=True, blank=True,
            on_delete=models.SET_NULL, verbose_name=_("Team"))

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
    not_publishable = models.BooleanField(_('Not publishable'), default=False)
    is_foi = models.BooleanField(_("is FoI request"), default=True)
    closed = models.BooleanField(_('is closed'), default=False)

    campaign = models.ForeignKey(
        Campaign, verbose_name=_('campaign'),
        null=True, blank=True, on_delete=models.SET_NULL
    )

    jurisdiction = models.ForeignKey(
        Jurisdiction,
        verbose_name=_('Jurisdiction'),
        null=True, on_delete=models.SET_NULL
    )
    language = models.CharField(
        max_length=10, blank=True,
        default=settings.LANGUAGE_CODE,
        choices=settings.LANGUAGES
    )

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
            ("moderate", _("Can moderate requests")),
        )

    # Custom Signals
    message_sent = django.dispatch.Signal()  # args: ["message", "user"]
    message_received = django.dispatch.Signal()  # args: ["message"]
    request_created = django.dispatch.Signal()  # args: []
    request_to_public_body = django.dispatch.Signal()  # args: []
    # status_changed providing args: [
    #    "status", "resolution", "data", "user",
    #    "previous_status", "previous_resolution"
    # ]
    status_changed = django.dispatch.Signal()
    became_overdue = django.dispatch.Signal()  # args: []
    became_asleep = django.dispatch.Signal()  # args: []
    public_body_suggested = django.dispatch.Signal()  # args: ["suggestion"]
    set_concrete_law = django.dispatch.Signal()  # args: ['name', 'user']
    made_public = django.dispatch.Signal()  # args: ['user']
    made_private = django.dispatch.Signal()  # args: ['user']
    escalated = django.dispatch.Signal()  # args: ['message', 'user']

    def __str__(self):
        return _("Request '%s'") % self.title

    @property
    def same_as_set(self):
        return FoiRequest.objects.filter(same_as=self)

    @property
    def messages(self):
        if not hasattr(self, "_messages") or self._messages is None:
            self.get_messages()
        return self._messages

    def get_messages(self, with_tags=False):
        qs = self.foimessage_set.select_related(
            "sender_user",
            "sender_public_body",
            "recipient_public_body"
        ).order_by("timestamp")
        if with_tags:
            qs = qs.prefetch_related('tags')

        self._messages = list(qs)
        return self._messages

    @property
    def messages_by_month(self):
        """
        Group messages by "month-year"-key, e.g. "2020-09".
        Add extra due date key.
        """
        groups = {}
        due_date = self.due_date
        has_overdue_messages = False
        for msg in self.messages:
            key = str(msg.timestamp)[:7]
            if key not in groups:
                groups[key] = {
                    'date': msg.timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                    'messages': [],
                    'show_overdue_message': False,  # shows "Deadline expired on ..." message
                    'indicate_overdue': False,  # shows "(overdue)" in message count label in timeline
                    'first_message_id': msg.get_html_id
                }
            groups[key]['messages'].append(msg)

            if due_date and msg.timestamp > due_date:
                has_overdue_messages = True

        # loop groups and set "has_overdue_message"
        if has_overdue_messages and due_date:
            for group_key, group in reversed(groups.items()):
                if group['date'] < due_date:
                    group['show_overdue_message'] = True
                    break
                if group['date'] > due_date:
                    group['indicate_overdue'] = True

        return list(groups.values())

    @property
    def status_representation(self):
        if self.due_date is not None:
            if self.is_overdue():
                return FilterStatus.OVERDUE
        return self.status if self.status != Status.RESOLVED else self.resolution

    @property
    def status_settable(self):
        return self.awaits_classification()

    @property
    def project_number(self):
        if self.project_order is not None:
            return self.project_order + 1
        return None

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

    def get_absolute_url_last_message(self):
        return self.get_absolute_url() + '#last'

    @property
    def url(self):
        return self.get_absolute_url()

    def get_absolute_short_url(self):
        return get_absolute_short_url(self.id)

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_absolute_domain_short_url(self):
        return get_absolute_domain_short_url(self.id)

    def get_secret(self):
        if not self.secret:
            self.secret = get_random_string(25)
            self.save()
        return self.secret

    def get_auth_link(self):
        from ..auth import get_foirequest_auth_code

        return "%s%s" % (settings.SITE_URL,
            reverse('foirequest-auth',
                kwargs={"obj_id": self.id,
                    "code": get_foirequest_auth_code(self)
                }))

    def get_upload_link(self):
        from ..auth import get_foirequest_upload_code

        return "%s%s" % (settings.SITE_URL,
            reverse('foirequest-publicbody_upload',
                kwargs={
                    "obj_id": self.id,
                    "code": get_foirequest_upload_code(self)
                }))

    def get_accessible_link(self):
        if self.visibility == self.VISIBILITY.VISIBLE_TO_REQUESTER:
            return self.get_auth_link()
        return self.get_absolute_domain_short_url()

    def get_autologin_url(self):
        return self.user.get_autologin_url(
            self.get_absolute_short_url()
        )

    def is_public(self):
        return self.visibility == self.VISIBILITY.VISIBLE_TO_PUBLIC

    def in_public_search_index(self):
        return (
            self.is_public() and self.is_foi and
            self.same_as_id is None and
            (self.project_id is None or self.project_order == 0)
        )

    def get_redaction_regexes(self):
        from ..utils import get_foi_mail_domains

        user = self.user
        domains = get_foi_mail_domains()
        email_regexes = [r'[\w\.\-]+@' + x for x in domains]
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
        all_regexes = [re.escape(a) for a in all_regexes]
        return json.dumps([a.strip() for a in all_regexes if a.strip()])

    def get_description(self):
        return redact_plaintext(self.description, user=self.user)

    def response_messages(self):
        return list(filter(lambda m: m.is_response, self.messages))

    def sent_messages(self):
        return list(filter(lambda m: not m.is_response, self.messages))

    def reply_received(self):
        return len(self.response_messages()) > 0

    def message_needs_status(self):
        mes = list(filter(lambda m: m.status is None, self.response_messages()))
        if not mes:
            return None
        return mes[0]

    def is_sent(self):
        return (
            not self.needs_public_body() and
            not self.awaits_user_confirmation()
        )

    def awaits_user_confirmation(self):
        return self.status == Status.AWAITING_USER_CONFIRMATION

    def status_is_final(self):
        return self.status == Status.RESOLVED

    def needs_public_body(self):
        return self.status == Status.PUBLICBODY_NEEDED

    def awaits_response(self):
        return self.status in (Status.AWAITING_RESPONSE, Status.ASLEEP)

    def is_actionable(self):
        return not self.needs_public_body() and (
            self.is_overdue() or self.reply_received()
        )

    @classmethod
    def get_throttle_config(cls):
        return settings.FROIDE_CONFIG.get('request_throttle', None)

    def should_apply_throttle(self):
        last_message = self.messages[-1]
        return not last_message.is_response or not self.is_actionable()

    def can_be_escalated(self):
        return self.law and self.law.mediator_id and self.is_actionable()

    def is_overdue(self):
        return self.was_overdue() and self.awaits_response()

    def is_successful(self):
        return self.resolution == Resolution.SUCCESSFUL

    def was_overdue(self):
        if self.due_date:
            return self.due_date < timezone.now()
        return False

    def has_been_refused(self):
        return self.resolution in (Resolution.REFUSED, Resolution.PARTIALLY_SUCCESSFUL)

    def awaits_classification(self):
        return self.status == Status.AWAITING_CLASSIFICATION

    def moderate_classification(self):
        return self.awaits_classification() and self.available_for_moderator_action()

    def available_for_moderator_action(self):
        ago = timezone.now() - MODERATOR_CLASSIFICATION_OFFSET
        return self.last_message < ago

    def set_awaits_classification(self):
        self.status = Status.AWAITING_CLASSIFICATION

    def follow_count(self):
        from froide.foirequestfollower.models import FoiRequestFollower
        return FoiRequestFollower.objects.filter(
            request=self, confirmed=True
        ).count()

    def public_date(self):
        if self.due_date:
            return self.due_date + timedelta(days=settings.FROIDE_CONFIG.get(
                'request_public_after_due_days', 14))
        return None

    def get_set_tags_form(self):
        from ..forms import TagFoiRequestForm
        return TagFoiRequestForm(tags=self.tags.all())

    def get_status_form(self, data=None):
        from ..forms import FoiRequestStatusForm

        if self.status not in (Status.AWAITING_RESPONSE, Status.RESOLVED):
            status = ''
        else:
            status = self.status
        return FoiRequestStatusForm(
            data=data,
            foirequest=self,
            initial={
                "status": status,
                'resolution': self.resolution,
                "costs": self.costs,
                "refusal_reason": self.refusal_reason
            })

    def public_body_suggestions_form(self):
        from ..forms import PublicBodySuggestionsForm
        return PublicBodySuggestionsForm(foirequest=self)

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
    def get_readable_status(cls, status, fallback=UNKNOWN_STATUS):
        return str(cls.STATUS_RESOLUTION_DICT.get(status, fallback).label)

    @classmethod
    def get_status_description(cls, status, fallback=UNKNOWN_STATUS):
        return str(cls.STATUS_RESOLUTION_DICT.get(status, fallback).description)

    def determine_visibility(self):
        if self.public:
            self.visibility = self.VISIBILITY.VISIBLE_TO_PUBLIC
        else:
            self.visibility = self.VISIBILITY.VISIBLE_TO_REQUESTER

    def set_status_after_change(self):
        if not self.user.is_active:
            self.status = Status.AWAITING_USER_CONFIRMATION
        else:
            self.determine_visibility()
            if self.public_body is None:
                self.status = Status.PUBLICBODY_NEEDED
            elif not self.public_body.confirmed:
                self.status = Status.AWAITING_PUBLICBODY_CONFIRMATION
            else:
                self.status = Status.AWAITING_RESPONSE
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
        self.message_sent.send(
            sender=self, message=message,
            user=self.user
        )

    def confirmed_public_body(self):
        send_now = self.set_status_after_change()
        self.save()
        if send_now:
            self.safe_send_first_message()
            return True
        return False

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

    def make_public(self, user=None):
        self.public = True
        self.visibility = 2
        self.save()
        self.made_public.send(sender=self, user=user)

    def set_overdue(self):
        self.became_overdue.send(sender=self)

    def set_asleep(self):
        self.status = Status.ASLEEP
        self.save()
        self.became_asleep.send(sender=self)

    def days_to_resolution(self):
        final = None
        mes = None
        resolutions = dict(Resolution.choices)
        for mes in self.response_messages():
            if mes.status == Status.RESOLVED or mes.status in resolutions:
                final = mes.timestamp
                break
        if final is None or mes is None:
            return None
        return (mes.timestamp - self.first_message).days


def get_absolute_short_url(pk):
    return reverse('foirequest-shortlink',
            kwargs={'obj_id': pk})


def get_absolute_domain_short_url(pk):
    return "%s%s" % (settings.SITE_URL, reverse('foirequest-shortlink',
            kwargs={'obj_id': pk}))
