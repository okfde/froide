import re

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.functional import cached_property
from django.template import Template, Context

from froide.foirequest.models import FoiMessage, MessageTag
from froide.helper.email_sending import MailIntent
from froide.publicbody.models import (
    Jurisdiction, PublicBody, Category
)
from froide.letter.models import LetterTemplate


def compile_text(text):
    regex = '|'.join(
        s.strip() for s in text.splitlines() if s.strip()
    )
    return re.compile(regex)


class Action(models.Model):
    name = models.CharField(max_length=255)

    label = models.CharField(
        max_length=255, blank=True
    )
    description = models.TextField(blank=True)
    snippet = models.TextField(blank=True)

    mail_intent = models.CharField(max_length=255, blank=True)

    tag = models.ForeignKey(
        MessageTag, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    letter_template = models.ForeignKey(
        LetterTemplate, null=True, blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = _('Action')
        verbose_name_plural = _('Actions')

    def __str__(self):
        return self.name

    @property
    def has_custom_notification(self):
        return bool(self.mail_intent)

    def get_description(self):
        return self.description

    def get_label(self):
        return self.label

    def get_snippet(self):
        return self.snippet

    def send_custom_notification(self, guidance):
        message = guidance.message
        request = message.request

        context = guidance.get_context()
        mi = MailIntent(
            self.mail_intent,
            ['message']
        )
        mi.send(
            user=request.user,
            context=context,
        )


def render_with_context(method):
    def wrapper(self):
        template_string = method(self)
        template = Template(template_string)
        return template.render(Context(self.get_context()))
    return wrapper


class Guidance(models.Model):
    message = models.ForeignKey(FoiMessage, on_delete=models.CASCADE)
    action = models.ForeignKey(
        Action, null=True, blank=True,
        on_delete=models.CASCADE
    )
    rule = models.ForeignKey(
        'Rule', null=True, blank=True,
        on_delete=models.SET_NULL
    )

    label = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    snippet = models.TextField(blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    timestamp = models.DateTimeField(default=timezone.now)
    notified = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Guidance')
        verbose_name_plural = _('Guidances')
        ordering = ('-timestamp',)
        permissions = (
            ("can_run_guidance", _('Can run guidance')),
        )

    def __str__(self):
        if self.action:
            return '{} -> {}'.format(self.action.name, self.message_id)
        return '{} -> {}'.format(self.label, self.message_id)

    def send_custom_notification(self):
        if self.action:
            if self.action.has_custom_notification:
                self.action.send_custom_notification(self)
                self.notified = True
                self.save()
                return True
        return False

    def get_context(self):
        request = self.message.request
        user = request.user
        ctx = {
            'foirequest': request,
            'publicbody': request.public_body,
            'user': user,
            'name': user.get_full_name(),
            'message': self.message,
            'action_url': '{}-guidance'.format(
                self.message.get_autologin_url()
            )
        }
        if self.action and self.action.letter_template_id:
            ctx['action_url'] = user.get_autologin_url(
                self.get_letter_url()
            )
        return ctx

    @render_with_context
    def get_description(self):
        if self.action:
            return self.action.description
        return self.description

    @render_with_context
    def get_label(self):
        if self.action:
            return self.action.label
        return self.label

    def has_snippet(self):
        if self.action:
            return bool(self.action.snippet)
        return bool(self.snippet)

    def has_letter(self):
        if self.action:
            return bool(self.action.letter_template_id)
        return False

    def get_letter_url(self):
        if self.action:
            return reverse(
                'letter-make',
                kwargs={
                    'letter_id': self.action.letter_template_id,
                    'message_id': self.message_id
                })
        return ''

    @render_with_context
    def get_snippet(self):
        if self.action:
            return self.action.snippet
        return self.snippet


class Rule(models.Model):
    name = models.CharField(max_length=255)
    priority = models.SmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    includes = models.TextField(blank=True)
    excludes = models.TextField(blank=True)

    has_tag = models.ForeignKey(
        MessageTag, null=True, blank=True,
        related_name='+',
        on_delete=models.SET_NULL
    )
    has_no_tag = models.ForeignKey(
        MessageTag, null=True, blank=True,
        related_name='+',
        on_delete=models.SET_NULL
    )

    references = models.CharField(max_length=255, blank=True)
    jurisdictions = models.ManyToManyField(
        Jurisdiction, blank=True
    )
    publicbodies = models.ManyToManyField(
        PublicBody, blank=True,
    )
    categories = models.ManyToManyField(
        Category, blank=True
    )

    actions = models.ManyToManyField(
        Action, blank=True
    )

    class Meta:
        verbose_name = _('Rule')
        verbose_name_plural = _('Rules')
        ordering = ('priority', 'name')

    def __str__(self):
        return self.name

    @cached_property
    def references_re(self):
        if not self.references:
            return None
        return re.compile(self.references)

    @cached_property
    def includes_re(self):
        if not self.includes:
            return None
        return compile_text(self.includes)

    @cached_property
    def excludes_re(self):
        if not self.excludes:
            return None
        return compile_text(self.excludes)
