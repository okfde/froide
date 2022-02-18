import re
from datetime import timedelta

from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone

from froide.accesstoken.models import AccessToken
from froide.helper.email_sending import (
    mail_middleware_registry,
    mail_registry,
    send_mail,
)

from . import account_canceled, account_merged
from .models import User
from .tasks import make_account_private_task

POSTCODE_RE = re.compile(r"(\d{5})\s+(.*)")
TRAILING_COMMA = re.compile(r"\s*,\s*$")

EXPIRE_UNCONFIRMED_USERS_AGE = timedelta(days=30)
CANCEL_DEACTIVATED_USERS_AGE = timedelta(days=100)


def send_mail_users(subject, body, users, **kwargs):
    for user in users:
        send_mail_user(subject, body, user, **kwargs)


class OnlyActiveUsersMailMiddleware:
    def should_mail(self, mail_intent, context, email_kwargs):
        user = context.get("user")
        if not user:
            # No user, not our concern here
            return

        if not email_kwargs.get("ignore_active", False) and not user.is_active:
            return False
        if not user.email:
            return False


mail_middleware_registry.register(OnlyActiveUsersMailMiddleware())


def send_mail_user(subject, body, user: User, ignore_active=False, **kwargs):
    if not ignore_active and not user.is_active:
        return
    if not user.email:
        return

    return send_mail(subject, body, user.email, bounce_check=False, **kwargs)


user_email = mail_registry.register("account/emails/user_email", ("subject", "body"))


def send_template_mail(user: User, subject: str, body: str, **kwargs):
    mail_context = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "name": user.get_full_name(),
        "url": user.get_autologin_url("/"),
    }
    user_subject = subject.format(**mail_context)
    user_body = body.format(**mail_context)
    return user_email.send(
        user=user, context={"subject": user_subject, "body": user_body}, **kwargs
    )


def make_account_private(user):
    user.private = True
    user.organization_name = ""
    user.organization_url = ""
    user.profile_text = ""
    if user.profile_photo:
        user.profile_photo.delete(save=False)
    user.save()

    make_account_private_task.delay(user.id)


def merge_accounts(old_user, new_user):
    for tag in old_user.tags.all():
        new_user.tags.add(tag)
    account_merged.send(sender=User, old_user=old_user, new_user=new_user)
    delete_all_unexpired_sessions_for_user(old_user)
    old_user.delete()


def move_ownership(model, attr, old_user, new_user, dupe=None):
    qs = model.objects.filter(**{attr: old_user})

    if dupe:
        collision_key = dupe[1]
        collision_list = model.objects.filter(**{attr: new_user}).values_list(
            collision_key, flat=True
        )
        qs = qs.exclude(**{"%s__in" % collision_key: collision_list})

    qs.update(**{attr: new_user})

    if dupe is None:
        return

    # rest are collisions, delete
    qs = model.objects.filter(**{attr: old_user}).delete()


def all_unexpired_sessions_for_user(user):
    user_sessions = []
    all_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    for session in all_sessions:
        session_data = session.get_decoded()
        if user.pk == session_data.get("_auth_user_id"):
            user_sessions.append(session.pk)
    return Session.objects.filter(pk__in=user_sessions)


def delete_all_unexpired_sessions_for_user(user, session_to_omit=None):
    session_list = all_unexpired_sessions_for_user(user)
    if session_to_omit is not None:
        session_list.exclude(session_key=session_to_omit.session_key)
    session_list.delete()


def start_cancel_account_process(user, delete=False):
    from .tasks import cancel_account_task

    user.private = True
    user.email = None
    user.tags.clear()
    user.is_active = False
    user.set_unusable_password()
    user.date_deactivated = timezone.now()

    user.save()
    delete_all_unexpired_sessions_for_user(user)

    # Asynchronously delete account
    # So more expensive anonymization can run in the background
    cancel_account_task.delay(user.pk, delete=delete)


def cancel_user(user, delete=False):
    with transaction.atomic():
        account_canceled.send(sender=User, user=user)

    delete_all_unexpired_sessions_for_user(user)

    if delete:
        user.delete()
        return

    user.organization_name = ""
    user.organization_url = ""
    user.private = True
    user.terms = False
    user.address = ""
    user.profile_text = ""
    user.profile_photo.delete()
    user.save()
    user.first_name = ""
    user.last_name = ""
    user.is_trusted = False
    user.is_staff = False
    user.is_superuser = False
    user.is_active = False
    user.date_deactivated = timezone.now()
    user.is_deleted = True
    user.date_left = timezone.now()
    user.email = None
    user.set_unusable_password()
    user.username = "u%s" % user.pk
    user.save()


def delete_unconfirmed_users():
    time_ago = timezone.now() - EXPIRE_UNCONFIRMED_USERS_AGE
    expired_users = User.objects.filter(
        is_active=False,
        is_deleted=False,
        last_login__isnull=True,
        date_joined__lt=time_ago,
    )
    for user in expired_users:
        start_cancel_account_process(user, delete=True)


def delete_deactivated_users():
    time_ago = timezone.now() - CANCEL_DEACTIVATED_USERS_AGE
    expired_users = User.objects.filter(
        is_active=False, is_deleted=False, date_deactivated__lt=time_ago
    )
    for user in expired_users:
        start_cancel_account_process(user)


def parse_address(address):
    match = POSTCODE_RE.search(address)
    if match is None:
        return {}
    postcode = match.group(1)
    city = match.group(2)
    refined = address.replace(match.group(0), "").strip().splitlines()
    street = refined or [""]
    street = TRAILING_COMMA.sub("", street[0])
    return {"address": street, "postcode": postcode, "city": city}


def find_duplicate_email_groups():
    from collections import defaultdict

    email_mapping = defaultdict(list)
    emails = User.objects.filter(email__isnull=False).values_list("email", flat=True)

    for email in emails:
        email_mapping[email.lower()].append(email)

    email_groups = []
    for emails in email_mapping.values():
        if len(emails) < 2:
            continue
        email_groups.append(emails)
    return email_groups


def check_account_compatibility(groups):
    def all_equal(li):
        if not li:
            return True
        first = li[0]
        return all(elem == first for elem in li)

    for emails in groups:
        users = User.objects.filter(email__in=emails).order_by("date_joined")
        name = [u.get_full_name().title() for u in users]
        private = [u.private for u in users]
        matches = all_equal([all_equal(li) for li in [name, private]])
        users[0].tags.add("duplicate-email-main")
        for user in users:
            user.tags.add("duplicate-email")
            if matches:
                user.tags.add("duplicate-email-match")
            else:
                if not all_equal(private):
                    user.tags.add("duplicate-email-private-mismatch")
                else:
                    user.tags.add("duplicate-email-other-mismatch")


def delete_expired_onetime_login_tokens():
    from .services import ONE_TIME_LOGIN_EXPIRY, ONE_TIME_LOGIN_PURPOSE

    time_ago = timezone.now() - ONE_TIME_LOGIN_EXPIRY
    AccessToken.objects.filter(
        purpose=ONE_TIME_LOGIN_PURPOSE, timestamp__lt=time_ago
    ).delete()
