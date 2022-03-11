from django.conf import settings
from django.db import models
from django.dispatch import Signal
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from froide.foirequest.models import FoiMessage

from .utils import inform_user_problem_resolved


class ProblemChoices(models.TextChoices):
    MESSAGE_NOT_DELIVERED = "message_not_delivered", _(
        "Your message was not delivered."
    )
    ATTACHMENT_BROKEN = "attachment_broken", _("The attachments don't seem to work.")
    REDACTION_NEEDED = "redaction_needed", _("More redactions are needed.")
    FOI_HELP_NEEDED = "foi_help_needed", _(
        "You need help to understand or reply to this message."
    )
    OTHER = "other", _("Something else...")
    NOT_FOI = "not_foi", _("This is not a proper FOI request.")
    NOT_NICE = "not_nice", _("Content is against netiquette.")
    INFO_OUTDATED = "info_outdated", _("Published information is outdated.")
    INFO_WRONG = "info_wrong", _("Published information is wrong.")
    BOUNCE_PUBLICBODY = "bounce_publicbody", _(
        "You received a bounce mail from the public body."
    )
    MAIL_INAUTHENTIC = "mail_inauthentic", _(
        "Received mail does not pass authenticity checks."
    )


def make_choices(value_list):
    return [(k, k.label) for k in value_list]


USER_PROBLEM_CHOICES = make_choices(
    [
        ProblemChoices.MESSAGE_NOT_DELIVERED,
        ProblemChoices.ATTACHMENT_BROKEN,
        ProblemChoices.REDACTION_NEEDED,
        ProblemChoices.FOI_HELP_NEEDED,
        ProblemChoices.OTHER,
    ]
)
EXTERNAL_PROBLEM_CHOICES = make_choices(
    [
        ProblemChoices.NOT_FOI,
        ProblemChoices.REDACTION_NEEDED,
        ProblemChoices.NOT_NICE,
        ProblemChoices.INFO_OUTDATED,
        ProblemChoices.INFO_WRONG,
        ProblemChoices.OTHER,
    ]
)

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

    def find_and_resolve(
        self, message=None, foirequest=None, kind=None, user=None, resolution=""
    ):
        if not message and not foirequest:
            return
        if not kind:
            return
        qs = self.get_queryset().filter(resolved=False)
        if message:
            qs = qs.filter(message=message)
        if foirequest:
            qs = qs.filter(message__request=foirequest)
        qs = qs.filter(kind=kind)
        for report in qs:
            report.resolve(user, resolution=resolution)


class ProblemReport(models.Model):
    PROBLEM = ProblemChoices

    message = models.ForeignKey(FoiMessage, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        blank=True,
        related_name="problems_reported",
    )
    kind = models.CharField(max_length=50, choices=ProblemChoices.choices)
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
        self.resolve_identical(user, resolution=resolution)
        return inform_user_problem_resolved(self)

    def resolve_identical(self, user, resolution=""):
        ProblemReport.objects.find_and_resolve(
            message=self.message, kind=self.kind, user=user, resolution=resolution
        )

    def escalate(self, user, escalation=""):
        self.moderator = user
        self.escalation = escalation
        self.escalated = timezone.now()
        self.save()
        escalated.send(sender=self)
