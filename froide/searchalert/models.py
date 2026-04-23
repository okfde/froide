import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.dispatch import Signal
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.translation import gettext_lazy as _

from dateutil.relativedelta import relativedelta

from froide.helper.email_sending import mail_registry

User = get_user_model()

REFERENCE_PREFIX = "alert-"
CONFIRM_EMAIL_TIME = timedelta(days=7)

AlertIdent = User | str


alert_confirm_subscribe_email = mail_registry.register(
    "searchalert/emails/confirm_subscribe",
    ("action_url", "alert", "user"),
)

alert_update_email = mail_registry.register(
    "searchalert/emails/alert_update",
    ("user", "alert", "total_count", "sections", "since_date"),
)


class AlertManager(models.Manager):
    def filter_active(self):
        return self.get_queryset().filter(
            models.Q(user__is_active=True)
            | models.Q(user__isnull=True, email_confirmed__isnull=False)
        )

    def filter_due(self):
        now = timezone.now()
        condition = models.Q()
        for val in AlertInterval.values:
            date = now - get_relative_delta(val)
            condition |= models.Q(interval=val) & models.Q(last_alert__lte=date)
        return self.filter_active().filter(condition)


class AlertInterval(models.TextChoices):
    DAILY = "daily", _("daily")
    WEEKLY = "weekly", _("weekly")
    MONTHLY = "monthly", _("monthly")


DEFAULT_INTERVAL = AlertInterval.WEEKLY


def get_relative_delta(interval: AlertInterval):
    if interval == AlertInterval.DAILY:
        return relativedelta(days=1)
    if interval == AlertInterval.WEEKLY:
        return relativedelta(days=7)
    return relativedelta(months=1)


class Alert(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("User"),
        on_delete=models.CASCADE,
    )
    email = models.EmailField(max_length=255, blank=True)
    email_confirmed = models.DateTimeField(null=True, default=None)
    created_at = models.DateTimeField(_("Timestamp of creation"), default=timezone.now)
    last_alert = models.DateTimeField(
        _("Timestamp of last alert"), default=timezone.now
    )
    interval = models.CharField(
        choices=AlertInterval.choices, blank=False, max_length=10
    )
    query = models.TextField(blank=False)
    sections = models.JSONField(default=dict, blank=True)
    context = models.JSONField(default=dict, blank=True)

    subscribed = Signal()  # args: []
    unsubscribing = Signal()  # args: []

    objects = AlertManager()

    class Meta:
        get_latest_by = "created_at"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                name="user_or_email",
                condition=(models.Q(user=None) & ~models.Q(email=""))
                | (~models.Q(user=None) & models.Q(email="")),
            )
        ]

    def __str__(self):
        return _("%(user)s alert %(query)s") % {
            "user": self.email or str(self.user),
            "query": self.query,
        }

    @property
    def description(self):
        sections = ", ".join(str(s.title) for s in self.get_sections())
        return _("{interval} search alert for “{query}” in {sections}").format(
            interval=self.get_interval_display(),
            query=self.query,
            sections=sections,
        )

    def get_full_name(self):
        if self.user:
            return self.user.get_full_name()
        return ""

    def get_email(self):
        if self.user:
            return self.user.email
        return self.email

    def get_context(self):
        return {
            "unsubscribe_url": self.get_unsubscribe_link(),
            "unsubscribe_reference": "{prefix}{pk}".format(
                prefix=REFERENCE_PREFIX, pk=self.id
            ),
        }

    def get_search_start_date(self):
        return self.last_alert or self.created_at

    def get_relative_delta(self):
        return get_relative_delta(self.interval)

    def is_due(self):
        due = timezone.now() - self.get_relative_delta()
        return self.last_alert <= due

    def get_section_keys(self):
        return {k for k, v in self.sections.items() if v}

    def get_sections(self):
        from .configuration import alert_registry

        return alert_registry.get_for_keys(self.get_section_keys())

    def get_ident(self) -> AlertIdent:
        return self.user or self.email

    def get_unsubscribe_link(self):
        return self.get_link(view="unsubscribe")

    def get_subscribe_link(self):
        return self.get_link()

    def get_change_link(self):
        return self.get_link(view="change")

    def get_link(self, view="confirm_subscribe"):
        url = reverse(
            "searchalert:{}".format(view),
            kwargs={
                "alert_id": self.id,
            }
            | ({"check": self.get_alert_secret()} if self.user is None else {}),
        )
        if self.user is not None:
            return self.user.get_autologin_url(url)
        return settings.SITE_URL + url

    def get_unsubscribe_url(self):
        return self.get_url("unsubscribe")

    def get_change_url(self):
        return self.get_url("change")

    def get_url(self, view="change"):
        return reverse(
            "searchalert:{}".format(view),
            kwargs={
                "alert_id": self.id,
            }
            | ({"check": self.get_alert_secret()} if self.user is None else {}),
        )

    def get_alert_secret(self):
        to_sign = [
            self.email,
            str(self.id),
        ]
        return hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            (".".join(to_sign)).encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    def check_secret(self, check):
        secret = self.get_alert_secret()
        return constant_time_compare(check, secret)

    def unsubscribe(self):
        self.unsubscribing.send(sender=self)
        self.delete()

    def subscribe(self, request=None):
        if self.email_confirmed:
            return
        if self.email:
            user = User.objects.filter(
                is_active=True, email_deterministic=self.email
            ).first()
            if user is not None:
                self.user = user
                self.email = ""
        self.email_confirmed = timezone.now()
        self.save()
        self.subscribed.send(sender=self, request=request)

    def send_confirm_alert_mail(self, user=None):
        user = User.objects.filter(
            is_active=True, email_deterministic=self.email
        ).first()
        context = {
            "user": user,
            "action_url": self.get_subscribe_link(),
            "alert": self,
        }
        context.update(self.context)
        context.update(self.get_context())
        alert_confirm_subscribe_email.send(
            email=self.email,
            subject=_("Please confirm alerts for “{query}”").format(query=self.query),
            context=context,
            priority=True,
        )

    def get_preview_updates(self):
        from .updates import collect_updates

        now = timezone.now()
        start_date = now - self.get_relative_delta()
        return list(collect_updates(self.query, start_date, self.get_section_keys()))

    def get_other_alerts(self):
        if self.user:
            return Alert.objects.exclude(id=self.id).filter(user=self.user)
        return Alert.objects.exclude(id=self.id).filter(
            email=self.email, email_confirmed__isnull=False
        )
