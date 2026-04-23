from froide.celery import app as celery_app


@celery_app.task
def update_alert_subscription(alert_id: int, preview=False):
    from .models import Alert
    from .updates import send_update

    try:
        alert = Alert.objects.get(id=alert_id)
    except Alert.DoesNotExist:
        pass
    if not alert.user and not alert.email_confirmed:
        return
    if alert.user and not alert.user.is_active:
        return
    if not alert.is_due() and not preview:
        return

    send_update(alert, preview=preview)


@celery_app.task
def search_alert_update_due():
    from .models import Alert

    due_alert_ids = Alert.objects.filter_due().values_list("id", flat=True)
    for alert_id in due_alert_ids:
        update_alert_subscription.delay(alert_id)


@celery_app.task
def cleanup_unconfirmed_email_search_alerts():
    from .utils import cleanup_unconfirmed_email_alerts

    cleanup_unconfirmed_email_alerts()
