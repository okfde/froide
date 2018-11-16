import re

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.utils.functional import cached_property

from froide.foirequest.models import FoiMessage, MessageTag
from froide.publicbody.models import (
    Jurisdiction, PublicBody, Category
)


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

    tag = models.ForeignKey(
        MessageTag, null=True, blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = _('Action')
        verbose_name_plural = _('Actions')

    def __str__(self):
        return self.name


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

    def get_description(self):
        if self.action:
            return self.action.description
        return self.description

    def get_label(self):
        if self.action:
            return self.action.label
        return self.label

    def get_snippet(self):
        if self.action:
            return self.action.snippet
        return self.snippet


class Rule(models.Model):
    name = models.CharField(max_length=255)
    priority = models.SmallIntegerField(default=1)

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
