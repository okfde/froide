from django.db import models
from django.contrib.postgres.fields import JSONField
from django.template import Template, Context
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from froide.foirequest.models import MessageTag


def render_with_context(method):
    def wrapper(self, context):
        template_string = method(self)
        template = Template(template_string)
        return template.render(Context(context))
    return wrapper


class LetterTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    post_instructions = models.TextField(blank=True)
    email_subject = models.CharField(max_length=255, blank=True)
    email_body = models.TextField(blank=True)

    form = JSONField(default=dict, blank=True)
    constraints = JSONField(default=dict, blank=True)

    subject = models.TextField(blank=True)
    body = models.TextField(blank=True)

    active = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    modified = models.DateTimeField(default=timezone.now)

    notes = models.TextField(blank=True)

    tag = models.ForeignKey(
        MessageTag, null=True, blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = _('letter template')
        verbose_name_plural = _('letter templates')

    def __str__(self):
        return self.name

    def get_fields(self):
        return self.form.get('fields', [])

    def get_constraints(self):
        return self.constraints.get('constraints', [])

    @render_with_context
    def get_description(self):
        return self.description

    @render_with_context
    def get_subject(self):
        return self.subject

    @render_with_context
    def get_body(self):
        return self.body

    @render_with_context
    def get_email_subject(self):
        return self.email_subject

    @render_with_context
    def get_email_body(self):
        return self.email_body

    @render_with_context
    def get_post_instructions(self):
        return self.post_instructions
