import json

from django.utils import timezone

from .models import CONFIRM_EMAIL_TIME, REFERENCE_PREFIX, Alert


def cleanup_unconfirmed_email_alerts():
    time_ago = timezone.now() - CONFIRM_EMAIL_TIME
    Alert.objects.exclude(
        email_confirmed__isnull=True, user__isnull=True, created_at__lt=time_ago
    ).delete()


def cancel_user(sender, user=None, **kwargs):
    if user is None:
        return
    Alert.objects.filter(user=user).delete()


def email_changed(sender=None, old_email=None, **kwargs):
    Alert.objects.filter(email=sender.email, email_confirmed__isnull=False).update(
        email="", user=sender
    )


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership

    move_ownership(
        Alert,
        "user_id",
        old_user.id,
        new_user.id,
    )


def handle_unsubscribe(sender, email, reference, **kwargs):
    if not reference.startswith(REFERENCE_PREFIX):
        # not for us
        return
    try:
        _alert_part, alert_id = reference.split(REFERENCE_PREFIX, 1)
    except ValueError:
        return
    try:
        alert_id = int(alert_id)
    except ValueError:
        return

    Alert.model.objects.filter(
        id=alert_id,
        email=email,
    ).delete()


def export_user_data(user):
    alerts = Alert.objects.filter(user=user)
    if not alerts:
        return
    yield (
        "alerts.json",
        json.dumps(
            [
                {
                    "created_at": alert.created_at.isoformat(),
                    "last_alert": alert.last_alert.isoformat()
                    if alert.last_alert
                    else None,
                    "interval": alert.interval,
                    "query": alert.query,
                    "sections": alert.sections,
                    "context": alert.context,
                }
                for alert in alerts
            ]
        ).encode("utf-8"),
    )
