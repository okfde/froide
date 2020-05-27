from django.conf import settings
from django.utils import translation

from froide.celery import app as celery_app

from .models import User


@celery_app.task
def cancel_account_task(user_pk, delete=False):
    from .utils import cancel_user

    translation.activate(settings.LANGUAGE_CODE)

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return

    cancel_user(user, delete=delete)


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
def merge_accounts_task(old_user_id, new_user_id):
    from .utils import merge_accounts

    try:
        old_user = User.objects.get(id=old_user_id)
    except User.DoesNotExist:
        return
    try:
        new_user = User.objects.get(id=new_user_id)
    except User.DoesNotExist:
        return

    merge_accounts(old_user, new_user)


@celery_app.task
def make_account_private_task(user_id):
    from . import account_made_private

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    account_made_private.send(sender=User, user=user)


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
    from .utils import send_template_mail

    chunks = chunker(user_ids, 200)
    for chunk in chunks:
        users = User.objects.filter(id__in=chunk)
        for user in users:
            send_template_mail(
                user, subject, body,
                priority=False
            )
