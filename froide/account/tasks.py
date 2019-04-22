from django.conf import settings
from django.utils import translation

from froide.celery import app as celery_app

from .models import User
from .utils import send_template_mail


@celery_app.task
def cancel_account_task(user_pk):
    from .utils import cancel_user

    translation.activate(settings.LANGUAGE_CODE)

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return

    cancel_user(user)


@celery_app.task
def delete_unconfirmed_users_task():
    from .utils import delete_unconfirmed_users

    translation.activate(settings.LANGUAGE_CODE)

    delete_unconfirmed_users()


@celery_app.task
def delete_deactivated_users_task():
    from .utils import delete_deactivated_users

    translation.activate(settings.LANGUAGE_CODE)

    delete_deactivated_users()


@celery_app.task
def account_maintenance_task():
    from .utils import (
        delete_unconfirmed_users, delete_deactivated_users
    )
    from .export import delete_all_expired_exports

    delete_unconfirmed_users()
    delete_deactivated_users()
    delete_all_expired_exports()


@celery_app.task
def start_export_task(user_id, notification_user_id=None):
    from .export import create_export

    translation.activate(settings.LANGUAGE_CODE)

    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return

    notification_user = None
    if notification_user_id is not None:
        try:
            notification_user = User.objects.get(id=notification_user_id)
        except User.DoesNotExist:
            pass

    create_export(user, notification_user=notification_user)


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


@celery_app.task
def send_bulk_mail(user_ids, subject, body):
    chunks = chunker(user_ids, 200)
    for chunk in chunks:
        users = User.objects.filter(id__in=chunk)
        for user in users:
            send_template_mail(user, subject, body)
