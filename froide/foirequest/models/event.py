from __future__ import unicode_literals

import json

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.utils.timesince import timesince
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.encoding import python_2_unicode_compatible

from froide.publicbody.models import PublicBody

from .request import FoiRequest


class FoiEventManager(models.Manager):
    def create_event(self, event_name, request, **context):
        assert event_name in FoiEvent.event_texts
        event = FoiEvent(request=request,
                public=request.is_visible(),
                event_name=event_name)
        event.user = context.pop("user", None)
        event.public_body = context.pop("public_body", None)
        event.context_json = json.dumps(context)
        event.save()
        return event


@python_2_unicode_compatible
class FoiEvent(models.Model):
    request = models.ForeignKey(FoiRequest,
            verbose_name=_("Freedom of Information Request"),
            on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
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
            "%(user)s reported costs of %(amount)s for this request."),
        "message_received": _(
            "Received an email from %(public_body)s."),
        "message_sent": _(
            "%(user)s sent a message to %(public_body)s."),
        "attachment_published": _(
            "%(user)s published an attachment on request %(request)s."),
        "request_redirected": _(
            "Request was redirected to %(public_body)s and due date has been reset."),
        "status_changed": _(
            "%(user)s set status to '%(status)s'."),
        "made_public": _(
            "%(user)s made the request '%(request)s' public."),
        "request_refused": _(
            "%(public_body)s refused to provide information on the grounds of %(reason)s."),
        "partially_successful": _(
            "%(public_body)s answered partially, but denied access to all information on the grounds of %(reason)s."),
        "became_overdue": _(
            "This request became overdue"),
        "set_concrete_law": _(
            "%(user)s set '%(name)s' as the information law for the request %(request)s."),
        "add_postal_reply": _(
            "%(user)s added a reply that was received via snail mail."),
        "escalated": _(
            "%(user)s filed a complaint to the %(public_body)s about the handling of this request %(request)s."),
        "deadline_extended": _(
            "The deadline of request %(request)s has been extended.")
    }

    class Meta:
        ordering = ('-timestamp',)
        verbose_name = _('Request Event')
        verbose_name_plural = _('Request Events')

    def __str__(self):
        return "%s - %s" % (self.event_name, self.request)

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.timestamp = timezone.now()
        super(FoiEvent, self).save(*args, **kwargs)

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
        context = json.loads(self.context_json)
        user = ""
        if self.user:
            user = self.user.display_name()
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

    def as_text(self):
        return self.event_texts[self.event_name] % self.get_context()

    def as_html(self):
        return mark_safe(self.event_texts[self.event_name] % self.get_html_context())
