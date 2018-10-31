"""
This contains a basic implementation of VERP and bounce detection
https://en.wikipedia.org/wiki/Variable_envelope_return_path

"""
from contextlib import closing
from datetime import datetime, timedelta
from io import BytesIO

from django.conf import settings
from django.core.mail import mail_managers
from django.core.signing import (
    TimestampSigner, SignatureExpired, BadSignature
)

from froide.helper.email_utils import EmailParser, get_unread_mails


BOUNCE_FORMAT = settings.FROIDE_CONFIG['bounce_format']
SIGN_SEP = ':'
SEP_REPL = '+'
MAX_BOUNCE_AGE = settings.FROIDE_CONFIG['bounce_max_age']

MAX_BOUNCE_COUNT = 20
HARD_BOUNCE_COUNT = 3
HARD_BOUNCE_PERIOD = timedelta(seconds=3 * 7 * 24 * 60 * 60)  # 3 weeks

SOFT_BOUNCE_COUNT = 5
SOFT_BOUNCE_PERIOD = timedelta(seconds=5 * 7 * 24 * 60 * 60)  # 5 weeks


def make_bounce_address(email):
    signer = TimestampSigner(sep=SIGN_SEP)
    value = signer.sign(email).split(SIGN_SEP, 1)[1]
    value = value.replace(SIGN_SEP, SEP_REPL)
    escaped_mail = email.replace('@', '=')
    token = '{}+{}'.format(value, escaped_mail)
    return BOUNCE_FORMAT.format(token=token)


def get_recipient_address_from_bounce(bounce_email):
    head, tail = BOUNCE_FORMAT.split('{token}')
    # Cut off head and tail of bounce formatting
    token = bounce_email[len(head):-len(tail)]
    parts = token.split(SEP_REPL)
    signature = SIGN_SEP.join(parts[:2])
    escaped_mail = SEP_REPL.join(parts[2:])
    parts = escaped_mail.rsplit('=', 1)
    email = '@'.join(parts)

    original = SIGN_SEP.join([email, signature])
    signer = TimestampSigner(sep=SIGN_SEP)
    try:
        signer.unsign(original, max_age=MAX_BOUNCE_AGE)
    except SignatureExpired:
        return email, None
    except BadSignature:
        return email, False
    return email, True


def check_bounce_mails():
    for rfc_data in get_unread_mails(
            settings.BOUNCE_EMAIL_HOST_IMAP,
            settings.BOUNCE_EMAIL_PORT_IMAP,
            settings.BOUNCE_EMAIL_ACCOUNT_NAME,
            settings.BOUNCE_EMAIL_ACCOUNT_PASSWORD,
            ssl=settings.BOUNCE_EMAIL_USE_SSL):
        process_bounce_mail(rfc_data)


def process_bounce_mail(mail_bytes):
    parser = EmailParser()
    with closing(BytesIO(mail_bytes)) as stream:
        email = parser.parse(stream)

    bounce_info = email.bounce_info
    if bounce_info.is_bounce:
        add_bounce_mail(email)
    else:
        if email.is_auto_reply:
            return
        mail_managers(
            'No bounce detected in bounce mailbox',
            email.subject
        )


def add_bounce_mail(email):
    from .models import Bounce

    recipient_list = set([
        get_recipient_address_from_bounce(addr) for name, addr in email.to
    ])
    for recipient, status in recipient_list:
        if status:
            bounce = Bounce.objects.update_bounce(recipient, email.bounce_info)
            check_user_deactivation(bounce)
        else:
            mail_managers(
                'Bad bounce address found',
                '%s: %s (%s)' % (email.subject, recipient, status)
            )


def get_bounce_stats(bounces, bounce_type='hard', start_date=None):
    filtered_bounces = [
        datetime.strptime(b['timestamp'][:19], '%Y-%m-%dT%H:%M:%S')
        for b in bounces if b['bounce_type'] == bounce_type
    ]
    filtered_bounces = [
        b for b in filtered_bounces if b >= start_date or start_date is None
    ]
    return len(filtered_bounces)


def check_bounce_status(bounces, bounce_type, period, threshold):
    start_date = datetime.now() - period
    count = get_bounce_stats(
        bounces, bounce_type=bounce_type, start_date=start_date
    )
    if count >= MAX_BOUNCE_COUNT:
        return True
    return count >= threshold


def check_user_deactivation(bounce):
    """
    Decide if current bounce state warrants deactivation
    """
    if not bounce.user:
        return

    if check_bounce_status(bounce.bounces, 'hard', HARD_BOUNCE_PERIOD,
                           HARD_BOUNCE_COUNT):
        bounce.user.deactivate()
        return True

    if check_bounce_status(bounce.bounces, 'soft', SOFT_BOUNCE_PERIOD,
                           SOFT_BOUNCE_COUNT):
        bounce.user.deactivate()
        return True

    return False
