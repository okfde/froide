from django.conf import settings
from django.db import models
from django.dispatch import Signal
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from froide.foirequest.models import FoiMessage

from .utils import inform_user_problem_resolved

USER_PROBLEM_CHOICES = [
    ("message_not_delivered", _("Your message was not delivered.")),
    ("attachment_broken", _("The attachments don't seem to work.")),
    ("redaction_needed", _("You need more redaction.")),
    ("foi_help_needed", _("You need help to understand or reply to this message.")),
    ("other", _("Something else...")),
]
EXTERNAL_PROBLEM_CHOICES = [
    ("not_foi", _("This is not a proper FOI request.")),
    ("redaction_needed", _("More redactions are needed.")),
    ("not_nice", _("Content is against netiquette.")),
    ("info_outdated", _("Published information is outdated.")),
    ("info_wrong", _("Published information is wrong.")),
    ("other", _("Something else...")),
]

AUTO_PROBLEM_CHOICES = [
    ("bounce_publicbody", _("You received a bounce mail from the public body.")),
]

PROBLEM_CHOICES = AUTO_PROBLEM_CHOICES + USER_PROBLEM_CHOICES

reported = Signal()
claimed = Signal()
resolved = Signal()
unclaimed = Signal()
escalated = Signal()


class ProblemReportManager(models.Manager):
    def report(self, **kwargs):
        report = ProblemReport.objects.create(**kwargs)
        reported.send(sender=report)
        return report


class ProblemReport(models.Model):
    message = models.ForeignKey(FoiMessage, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        blank=True,
        related_name="problems_reported",
    )
    kind = models.CharField(
        max_length=50, choices=(PROBLEM_CHOICES + EXTERNAL_PROBLEM_CHOICES)
    )
    timestamp = models.DateTimeField(default=timezone.now)
    auto_submitted = models.BooleanField(default=False)
    resolved = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    resolution = models.TextField(blank=True)
    resolution_timestamp = models.DateTimeField(null=True, blank=True)
    claimed = models.DateTimeField(null=True, blank=True)
    escalation = models.TextField(blank=True)
    escalated = models.DateTimeField(null=True, blank=True)
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        blank=True,
        related_name="problems_moderated",
    )

    objects = ProblemReportManager()

    class Meta:
        ordering = ("-timestamp",)
        verbose_name = _("problem report")
        verbose_name_plural = _("problem reports")

    def __str__(self):
        return self.kind

    def get_absolute_url(self):
        return self.message.get_absolute_short_url()

    def get_absolute_domain_url(self):
        return self.message.get_absolute_domain_short_url()

    @property
    def is_requester(self):
        return self.user_id == self.message.request.user_id

    def related_publicbody_id(self):
        if self.message.is_response:
            return self.message.sender_public_body_id
        return self.message.recipient_public_body_id

    def claim(self, user):
        self.claimed = timezone.now()
        self.moderator = user
        self.save()
        claimed.send(sender=self)

    def unclaim(self, user):
        self.moderator = None
        self.claimed = None
        self.save()
        unclaimed.send(sender=self)

    def resolve(self, user, resolution=""):
        self.resolved = True
        self.resolution = resolution
        self.resolution_timestamp = timezone.now()
        self.moderator = user
        self.save()
        resolved.send(sender=self)
        return inform_user_problem_resolved(self)

    def escalate(self, user, escalation=""):
        self.moderator = user
        self.escalation = escalation
        self.escalated = timezone.now()
        self.save()
        escalated.send(sender=self)
