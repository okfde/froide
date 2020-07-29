from collections import namedtuple

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.timesince import timesince
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.contrib.postgres.fields import JSONField

from froide.publicbody.models import PublicBody

from . import FoiRequest, FoiMessage

EventDetail = namedtuple('EventDetail', 'description')

UNKNOWN_EVENT = EventDetail(description=_('unknown'))


class EventName(models.TextChoices):
    PUBLIC_BODY_SUGGESTED = "public_body_suggested", _('a public body was suggested')
    REPORTED_COSTS = "reported_costs", _('costs were reported for this request')

    MESSAGE_RECEIVED = "message_received", _('a message was received')
    MESSAGE_SENT = "message_sent", _('a message was sent')
    MESSAGE_APPROVED = "message_approved", _('hidden message was approved')
    MESSAGE_EDITED = "message_edited", _('message was edited')
    MESSAGE_REDACTED = "message_redacted", _('message was redacted')
    MESSAGE_RESENT = "message_resent", _('message was resent')

    ATTACHMENT_UPLOADED = "attachment_uploaded", _('attachments were uploaded')
    ATTACHMENT_PUBLISHED = "attachment_published", _('an attachment was published')
    ATTACHMENT_REDACTED = "attachment_redacted", _('an attachment was redacted')
    ATTACHMENT_DELETED = "attachment_deleted", _('an attachment was deleted')
    DOCUMENT_CREATED = "document_created", _('a document was created')
    REQUEST_REDIRECTED = "request_redirected", _('the request was redirected')
    STATUS_CHANGED = "status_changed", _('the status was changed')
    MADE_PUBLIC = "made_public", _('the request was made public')
    REQUEST_REFUSED = "request_refused", _('the request was marked as refused')
    PARTIALLY_SUCCESSFUL = "partially_successful", _(
        'the request was marked '
        'as partially successful')
    BECAME_OVERDUE = "became_overdue", _('request became overdue')
    SET_CONCRETE_LAW = "set_concrete_law", _('a concrete law was set')
    ADD_POSTAL_REPLY = "add_postal_reply", _('a postal reply was added')
    ADD_POSTAL_MESSAGE = "add_postal_message", _('a postal message was sent')
    ESCALATED = "escalated", _('the request was escalated to mediator')
    DEADLINE_EXTENDED = "deadline_extended", _(
        'the deadline for the request '
        'was extended')
    MARK_NOT_FOI = "mark_not_foi", _('the request was marked as not')
    SENDER_CHANGED = "sender_changed", _('sender of message was changed')
    RECIPIENT_CHANGED = "recipient_changed", _('recipient of message was changed')


EVENT_KEYS = dict(EventName.choices).keys()

EVENT_DETAILS = {
    EventName.PUBLIC_BODY_SUGGESTED: EventDetail(
        _("%(user)s suggested %(public_body)s for the request '%(request)s'")
    ),
    EventName.REPORTED_COSTS: EventDetail(_(
        "%(user)s reported costs of %(amount)s for this request.")
    ),
    EventName.MESSAGE_RECEIVED: EventDetail(_(
        "Received a message from %(public_body)s.")
    ),
    EventName.MESSAGE_SENT: EventDetail(_(
        "%(user)s sent a message to %(public_body)s.")
    ),
    EventName.ATTACHMENT_PUBLISHED: EventDetail(_(
        "%(user)s published an attachment on request %(request)s.")
    ),
    EventName.REQUEST_REDIRECTED: EventDetail(_(
        "Request was redirected to %(public_body)s and due date has been reset.")
    ),
    EventName.STATUS_CHANGED: EventDetail(_(
        "%(user)s set status to '%(status)s'.")
    ),
    EventName.MADE_PUBLIC: EventDetail(_(
        "%(user)s made the request '%(request)s' public.")
    ),
    EventName.REQUEST_REFUSED: EventDetail(_(
        "%(public_body)s refused to provide information on the grounds of %(reason)s.")
    ),
    EventName.PARTIALLY_SUCCESSFUL: EventDetail(_(
        "%(public_body)s answered partially, but denied access to all "
        "information on the grounds of %(reason)s.")
    ),
    EventName.BECAME_OVERDUE: EventDetail(_(
        "This request became overdue")
    ),
    EventName.SET_CONCRETE_LAW: EventDetail(_(
        "%(user)s set '%(name)s' as the information law for the request.")
    ),
    EventName.ADD_POSTAL_REPLY: EventDetail(_(
        "%(user)s added a reply that was received via postal mail.")
    ),
    EventName.ADD_POSTAL_MESSAGE: EventDetail(_(
        "%(user)s has sent a postal mail.")
    ),
    EventName.ESCALATED: EventDetail(_(
        "%(user)s filed a complaint to the %(public_body)s about the handling "
        "of this request %(request)s.")
    ),
    EventName.DEADLINE_EXTENDED: EventDetail(_(
        "The deadline of request %(request)s has been extended."))
}


class FoiEventManager(models.Manager):
    def create_event(self, event_name, foirequest, message=None, user=None,
                     public_body=None, **context):
        assert event_name in EVENT_KEYS
        event = FoiEvent(
            request=foirequest,
            public=foirequest.is_public(),
            event_name=event_name,
            user=user,
            message=message,
            public_body=public_body,
            context=context
        )
        event.save()
        return event


class FoiEvent(models.Model):
    EVENTS = EventName

    request = models.ForeignKey(
        FoiRequest,
        verbose_name=_("Freedom of Information Request"),
        on_delete=models.CASCADE
    )
    message = models.ForeignKey(
        FoiMessage,
        null=True, blank=True,
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True,
        on_delete=models.SET_NULL, blank=True,
        verbose_name=_("User")
    )
    public_body = models.ForeignKey(
        PublicBody, null=True,
        on_delete=models.SET_NULL, blank=True,
        verbose_name=_("Public Body")
    )
    public = models.BooleanField(_("Is Public?"), default=True)
    event_name = models.CharField(_("Event Name"), max_length=255)
    timestamp = models.DateTimeField(_("Timestamp"), default=timezone.now)
    context = JSONField(_("Context JSON"))

    objects = FoiEventManager()

    class Meta:
        ordering = ('-timestamp',)
        verbose_name = _('Request Event')
        verbose_name_plural = _('Request Events')

    def __str__(self):
        return "%s - %s" % (self.event_name, self.request)

    def get_html_id(self):
        # Translators: Hash part of Event URL
        return "%s-%d" % (str(_("event")), self.id)

    def get_absolute_url(self):
        return "%s#%s" % (self.request.get_absolute_url(),
                self.get_html_id())

    def get_context(self):
        context = getattr(self, "_context", None)
        if context is not None:
            return context
        context = dict(self.context)
        user = ""
        if self.user:
            user = self.user.display_name()
        pb = ""
        if self.public_body:
            pb = self.public_body.name
        context.update({
            "user": user,
            "public_body": pb,
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
            if not self.user.private:
                context['user'] = link(self.user.get_absolute_url(),
                        context['user'])
        if self.public_body:
            context['public_body'] = link(self.public_body.get_absolute_url(),
                    context['public_body'])
        context['request'] = link(self.request.get_absolute_url(),
                context['request'])
        self._html_context = context
        return context

    @property
    def detail(self):
        try:
            return EVENT_DETAILS[self.event_name]
        except KeyError:
            return UNKNOWN_EVENT

    def as_text(self):
        return self.detail.description % self.get_context()

    def as_html(self):
        return mark_safe(self.detail.description % self.get_html_context())
