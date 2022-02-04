"""
This contains a basic implementation of VERP and bounce detection
https://en.wikipedia.org/wiki/Variable_envelope_return_path

"""
import base64
import datetime
import time
from contextlib import closing
from email.utils import parseaddr
from io import BytesIO
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import mail_managers
from django.core.mail.message import sanitize_address
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.core.validators import validate_email
from django.utils import timezone
from django.utils.crypto import salted_hmac

from froide.helper.email_parsing import parse_email, parse_header_field
from froide.helper.email_utils import (
    BounceResult,
    classify_bounce_status,
    find_status_from_diagnostic,
    get_mail_client,
    get_unread_mails,
)

from .models import Bounce
from .signals import email_bounced, email_unsubscribed, user_email_bounced

BOUNCE_FORMAT = settings.FROIDE_CONFIG["bounce_format"]
UNSUBSCRIBE_FORMAT = settings.FROIDE_CONFIG["unsubscribe_format"]
UNSUBSCRIBE_PREFIX = "unsubscribe-"

SIGN_SEP = ":"
SEP_REPL = "+"
MAX_BOUNCE_AGE = settings.FROIDE_CONFIG["bounce_max_age"]

MAX_BOUNCE_COUNT = 20
HARD_BOUNCE_COUNT = 3
HARD_BOUNCE_PERIOD = datetime.timedelta(seconds=3 * 7 * 24 * 60 * 60)  # 3 weeks

SOFT_BOUNCE_COUNT = 5
SOFT_BOUNCE_PERIOD = datetime.timedelta(seconds=5 * 7 * 24 * 60 * 60)  # 5 weeks


def b32_encode(s):
    return base64.b32encode(s).strip(b"=")


def base32_hmac(salt, value, key):
    return b32_encode(salted_hmac(salt, value, key).digest()).decode()


def int_to_bytes(x):
    return x.to_bytes((x.bit_length() + 7) // 8, "big")


def bytes_to_int(xbytes):
    return int.from_bytes(xbytes, "big")


class CustomTimestampSigner(TimestampSigner):
    """
    Signs in base32 so that only lower case characters are used.
    """

    def signature(self, value):
        return base32_hmac(self.salt + "signer", value, self.key)

    def timestamp(self):
        return base64.b32encode(int_to_bytes(int(time.time()))).decode("ascii")

    def unsign(self, value, max_age=None):
        """
        Retrieve original value and check it wasn't signed more
        than max_age seconds ago.
        """
        result = super(TimestampSigner, self).unsign(value)
        value, timestamp = result.rsplit(self.sep, 1)
        timestamp = bytes_to_int(base64.b32decode(timestamp))
        if max_age is not None:
            if isinstance(max_age, datetime.timedelta):
                max_age = max_age.total_seconds()
            # Check timestamp is not older than max_age
            age = time.time() - timestamp
            if age > max_age:
                raise SignatureExpired("Signature age %s > %s seconds" % (age, max_age))
        return value


def make_bounce_address(email):
    _, email = parseaddr(email)
    return make_signed_address(email)


def make_unsubscribe_header(email, reference):
    _, email = parseaddr(email)
    unsub_email = make_unsubscribe_address(email)
    return "<mailto:{email}?subject={subject}>".format(
        email=unsub_email,
        subject=quote(
            "{prefix}{reference}".format(prefix=UNSUBSCRIBE_PREFIX, reference=reference)
        ),
    )


def make_unsubscribe_address(email):
    return make_signed_address(email, email_format=UNSUBSCRIBE_FORMAT)


def make_signed_address(email, email_format=BOUNCE_FORMAT):
    signer = CustomTimestampSigner(sep=SIGN_SEP)
    email = email.lower()
    # Sanitize address to convert unicode domains to punycode
    email = sanitize_address(email, "utf-8")
    value = signer.sign(email).split(SIGN_SEP, 1)[1]
    value = value.replace(SIGN_SEP, SEP_REPL).lower()
    # normalize email to lower case, some bounces may go to lower case
    escaped_mail = email.replace("@", "=")
    token = "{}+{}".format(value, escaped_mail)
    return email_format.format(token=token)


def get_signing_methods(email, signature):
    """
    This tries two different signing methods
    1. Custom signer using base32 alphabet
    2. standard django TimestampSigner
    """
    # base32 alphabet is uppercase
    original = SIGN_SEP.join([email.lower(), signature.upper()])
    yield CustomTimestampSigner, original
    original = SIGN_SEP.join([email, signature])
    yield TimestampSigner, original


def get_recipient_address_from_bounce(bounce_email):
    return get_original_email_from_signed(bounce_email)


def get_recipient_address_from_unsubscribe(unsub_email):
    return get_original_email_from_signed(
        unsub_email, email_format=UNSUBSCRIBE_FORMAT, max_age=None
    )


def get_original_email_from_signed(
    signed_email, email_format=BOUNCE_FORMAT, max_age=MAX_BOUNCE_AGE
):
    head, tail = email_format.split("{token}")
    # Cut off head and tail of bounce formatting
    token = signed_email[len(head) : -len(tail)]
    parts = token.split(SEP_REPL)
    signature = SIGN_SEP.join(parts[:2])

    escaped_mail = SEP_REPL.join(parts[2:])
    email_parts = escaped_mail.rsplit("=", 1)
    email = "@".join(email_parts)

    for klass, original in get_signing_methods(email, signature):
        signer = klass(sep=SIGN_SEP)
        try:
            signer.unsign(original, max_age=max_age)
            return email, True
        except SignatureExpired:
            return email, None
        except BadSignature:
            continue
    return email, False


def check_bounce_mails():
    with get_mail_client(
        settings.BOUNCE_EMAIL_HOST_IMAP,
        settings.BOUNCE_EMAIL_PORT_IMAP,
        settings.BOUNCE_EMAIL_ACCOUNT_NAME,
        settings.BOUNCE_EMAIL_ACCOUNT_PASSWORD,
        ssl=settings.BOUNCE_EMAIL_USE_SSL,
    ) as client:
        for _mail_uid, rfc_data in get_unread_mails(client, flag=False):
            process_bounce_mail(rfc_data)


def check_unsubscribe_mails():
    with get_mail_client(
        settings.UNSUBSCRIBE_EMAIL_HOST_IMAP,
        settings.UNSUBSCRIBE_EMAIL_PORT_IMAP,
        settings.UNSUBSCRIBE_EMAIL_ACCOUNT_NAME,
        settings.UNSUBSCRIBE_EMAIL_ACCOUNT_PASSWORD,
        ssl=settings.UNSUBSCRIBE_EMAIL_USE_SSL,
    ) as client:
        for _mail_uid, rfc_data in get_unread_mails(client, flag=False):
            process_unsubscribe_mail(rfc_data)


def process_unsubscribe_mail(mail_bytes):
    with closing(BytesIO(mail_bytes)) as stream:
        email = parse_email(stream)
    recipient_list = list(
        set([get_recipient_address_from_unsubscribe(addr) for name, addr in email.to])
    )
    if len(recipient_list) != 1:
        return
    recipient, status = recipient_list[0]
    if not status:
        return
    subject = email.subject
    if not subject.startswith(UNSUBSCRIBE_PREFIX):
        return
    _, reference = subject.split(UNSUBSCRIBE_PREFIX, 1)
    email_unsubscribed.send(sender=None, email=recipient, reference=reference)


def process_bounce_mail(mail_bytes):
    with closing(BytesIO(mail_bytes)) as stream:
        email = parse_email(stream)

    bounce_info = email.bounce_info
    if bounce_info.is_bounce:
        add_bounce_mail(email)
    else:
        if email.is_auto_reply:
            return
        mail_managers("No bounce detected in bounce mailbox", email.subject)


def add_bounce_mail(email):
    recipient_list = set(
        [get_recipient_address_from_bounce(addr) for name, addr in email.to]
    )
    for recipient, status in recipient_list:
        if status:
            update_bounce(email, recipient)
        else:
            mail_managers(
                "Bad bounce address found",
                "%s: %s (%s)" % (email.subject, recipient, status),
            )


def update_bounce(email, recipient):
    bounce = Bounce.objects.update_bounce(recipient, email.bounce_info)
    should_deactivate = check_deactivation_condition(bounce)

    email_bounced.send(
        sender=Bounce, bounce=bounce, should_deactivate=should_deactivate
    )
    if bounce.user:
        user_email_bounced.send(
            sender=Bounce, bounce=bounce, should_deactivate=should_deactivate
        )


def get_bounce_stats(bounces, bounce_type="hard", start_date=None):
    filtered_bounces = [
        datetime.datetime.strptime(b["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")
        for b in bounces
        if b["bounce_type"] == bounce_type
    ]
    filtered_bounces = [
        b for b in filtered_bounces if b >= start_date or start_date is None
    ]
    return len(filtered_bounces)


def check_bounce_status(bounces, bounce_type, period, threshold):
    start_date = datetime.datetime.now() - period
    count = get_bounce_stats(bounces, bounce_type=bounce_type, start_date=start_date)
    if count >= MAX_BOUNCE_COUNT:
        return True
    return count >= threshold


def check_deactivation_condition(bounce):
    """
    Decide if current bounce state warrants deactivation
    """

    if check_bounce_status(
        bounce.bounces, "hard", HARD_BOUNCE_PERIOD, HARD_BOUNCE_COUNT
    ):
        return True

    if check_bounce_status(
        bounce.bounces, "soft", SOFT_BOUNCE_PERIOD, SOFT_BOUNCE_COUNT
    ):
        return True

    return False


def handle_smtp_error(exc):
    """
    Handle SMTPRecipientsRefused exceptions
    """
    recipients = exc.recipients
    for recipient, info in recipients.items():
        recipient = parse_header_field(recipient)
        try:
            validate_email(recipient)
        except ValidationError:
            continue
        code, message = info
        message = message.decode("utf-8")
        status = find_status_from_diagnostic(message)
        if status == (5, 7, 1) or "Sender address rejected" in message:
            # Sender address rejected, raise Error
            raise exc
        if status == (5, 1, 1) or "Recipient address rejected" in message:
            bounce_type = classify_bounce_status(status)
            bounce_info = BounceResult(
                status=status,
                bounce_type=bounce_type,
                is_bounce=True,
                diagnostic_code=code,
                timestamp=timezone.now(),
            )
            Bounce.objects.update_bounce(recipient, bounce_info)
            continue
        raise exc
    return True
