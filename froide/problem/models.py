from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from froide.foirequest.models import FoiMessage


USER_PROBLEM_CHOICES = [
    ('message_not_delivered', _('Your message was not delivered.')),
    ('attachment_broken', _('The attachments don\'t seem to work.')),
    ('need_unpublish', _('You want to unpublish the request.')),
    ('redaction_needed', _('You need more redaction.')),
    ('foi_help_needed', _('You need help to understand or reply to this message.')),
    ('other', _('Something else...')),
]

AUTO_PROBLEM_CHOICES = [
    ('bounce_publicbody', _('You received a bounce mail from the public body.')),
]

PROBLEM_CHOICES = AUTO_PROBLEM_CHOICES + USER_PROBLEM_CHOICES


class ProblemReport(models.Model):
    message = models.ForeignKey(
        FoiMessage, on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, on_delete=models.SET_NULL,
        blank=True
    )
    kind = models.CharField(
        max_length=50, choices=PROBLEM_CHOICES
    )
    timestamp = models.DateTimeField(default=timezone.now)
    auto_submitted = models.BooleanField(default=False)
    resolved = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    resolution = models.TextField(blank=True)

    class Meta:
        ordering = ('-timestamp',)
        verbose_name = _('problem report')
        verbose_name_plural = _('problem reports')

    def __str__(self):
        return self.kind

    def get_absolute_url(self):
        return self.message.get_absolute_short_url()

    def get_absolute_domain_url(self):
        return self.message.get_absolute_domain_short_url()
