import contextlib
import imaplib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from enum import Enum
from typing import Iterator, NamedTuple, Optional, Tuple, Union

from django.conf import settings
from django.utils import timezone

AUTO_REPLY_SUBJECT_REGEX = settings.FROIDE_CONFIG.get("auto_reply_subject_regex", None)
AUTO_REPLY_EMAIL_REGEX = settings.FROIDE_CONFIG.get("auto_reply_email_regex", None)
AUTO_REPLY_HEADERS = (
    ("X-Autoreply", None),
    ("X-Autorespond", None),
    ("Auto-Submitted", "auto-replied"),
)
SMTP_FULL_STATUS_RE = re.compile(r"([45]\d{2}) (\d\.\d+\.\d+)")
SMTP_DIAGNOSTIC_STATUS_RE = re.compile(r"smtp; (\d{3})")
SMTP_EXTENDED_STATUS_RE = re.compile(r"(\d\.\d+\.\d+)", re.IGNORECASE)
BOUNCE_TEXT = re.compile(
    r"""5\d{2}\ Requested\ action\ not\ taken |
RESOLVER\.ADR\.RecipNotFound |
mailbox\ unavailable |
RCPT\ TO\ command |
permanent\ error |
SMTP\ error |
552 5.2.2
original\ message |
Return-Path:\ # If headers are given in verbose
""",
    re.X | re.I,
)
BOUNCE_TEXT_THRESHOLD = 3  # At least three occurences of above patterns
BOUNCE_HEADERS = (
    "Action",
    "Content-Description",
    "Diagnostic-Code",
    "Final-Recipient",
    "X-Failed-Recipients",
    "Received",
    "Remote-Mta",
    "Remote-MTA",
    "Reporting-MTA",
    "Reporting-Mta",
    "Status",
)


class SmtpBasicStatus(NamedTuple):
    class_: int
    subject: int
    detail: int

    @classmethod
    def from_string(cls, dsn_string):
        return cls(*[int(x) for x in dsn_string])


class SmtpExtendedStatus(NamedTuple):
    class_: int
    subject: int
    detail: int

    @classmethod
    def from_string(cls, dsn_string):
        return cls(*[int(x) for x in dsn_string.split(".")])


GENERIC_ERROR = SmtpExtendedStatus(5, 0, 0)
MAILBOX_FULL = SmtpBasicStatus(5, 5, 2)
MAILBOX_FULL_EXTENDED = [SmtpExtendedStatus(5, 2, 2), SmtpExtendedStatus(4, 2, 2)]


class BounceType(str, Enum):
    UNKNOWN = "unknown"
    SOFT = "soft"
    HARD = "hard"


class BounceResult(NamedTuple):
    status: SmtpExtendedStatus
    basic_status: SmtpBasicStatus
    is_bounce: bool
    timestamp: datetime
    bounce_type: BounceType = BounceType.UNKNOWN
    diagnostic_code: Optional[str] = None


@dataclass
class SmtpStatus:
    basic: SmtpBasicStatus | None
    extended: SmtpExtendedStatus | None

    def __eq__(self, other: "SmtpStatus") -> bool:
        return self.basic == other.basic and self.extended == other.extended

    def is_more_expressive(self, other: "SmtpStatus") -> bool:
        if self.extended is None and other.extended is not None:
            return True
        if self.is_generic_error() and not other.is_generic_error():
            return True
        if self.basic is None and other.basic is not None:
            return True
        return False

    def is_generic_error(self):
        if self.extended and self.extended == GENERIC_ERROR:
            return True
        return False

    def is_mailbox_full(self):
        if self.basic and self.basic == MAILBOX_FULL:
            return True
        elif self.extended and self.extended in MAILBOX_FULL_EXTENDED:
            return True
        return False

    def is_sender_rejected(self):
        return self.extended and self.extended == (5, 7, 1)

    def is_recipient_rejected(self):
        return self.extended and self.extended == (5, 1, 1)

    def get_bounce_type(self: "SmtpStatus") -> BounceType:
        if self.is_mailbox_full():
            return BounceType.SOFT

        dsn_class = None
        if self.extended is not None:
            dsn_class = self.extended.class_
        elif self.basic is not None:
            dsn_class = self.basic.class_

        if dsn_class is not None:
            if dsn_class == 5:
                return BounceType.HARD
            elif dsn_class == 4:
                return BounceType.SOFT
        return BounceType.UNKNOWN

    def to_bounce_result(
        self, is_bounce=None, diagnostic_code=None, date=None
    ) -> BounceResult:
        bounce_type = self.get_bounce_type()
        return BounceResult(
            status=self.extended,
            basic_status=self.basic,
            bounce_type=bounce_type,
            is_bounce=bounce_type != BounceType.UNKNOWN
            if is_bounce is None
            else is_bounce,
            diagnostic_code=diagnostic_code,
            timestamp=date or timezone.now(),
        )


class AuthenticityCheck(Enum):
    SPF = "SPF"
    DKIM = "DKIM"
    DMARC = "DMARC"


@dataclass
class AuthenticityStatus:
    check: AuthenticityCheck
    status: str
    failed: bool
    details: str

    def __str__(self):
        return self.details

    def to_dict(self):
        return {
            "check": self.check.value,
            "status": self.status,
            "failed": self.failed,
            "details": self.details,
        }


UID_RE = re.compile(r"UID\s+(?P<uid>\d+)")


def get_imap_message_uid(flag_bytes):
    match = UID_RE.search(flag_bytes.decode())
    if match is None:
        return None
    return match.group("uid")


@contextlib.contextmanager
def get_mail_client(host, port, user, password, ssl=True):
    klass = imaplib.IMAP4
    if ssl:
        klass = imaplib.IMAP4_SSL
    con = klass(host, port)
    con.login(user, password)

    yield con

    con.logout()


def get_unread_mails(
    mailbox: Union[imaplib.IMAP4_SSL, imaplib.IMAP4], flag=False
) -> Iterator[Tuple[Optional[str], bytes]]:
    status, count = mailbox.select("Inbox")
    typ, data = mailbox.search(None, "UNSEEN")
    for num in data[0].split():
        status, data = mailbox.fetch(num, "(BODY[] UID)")
        uid = get_imap_message_uid(data[0][0])
        if flag:
            mailbox.store(num, "+FLAGS", "\\Flagged")
        yield uid, data[0][1]

    mailbox.close()


def delete_mails_by_recipient(
    mailbox: Union[imaplib.IMAP4_SSL, imaplib.IMAP4],
    recipient_mail: str,
    expunge=False,
    sanity_check=100,
) -> int:
    """
    Delete all mail to recipient_mail in IMAP mailbox
    """
    assert recipient_mail

    status, count = mailbox.select("Inbox")
    # find all messages to recipient mail
    status, [msg_ids] = mailbox.search(
        None, '(OR TO "{recipient}" CC "{recipient}")'.format(recipient=recipient_mail)
    )
    msg_ids = [x.strip() for x in msg_ids.decode("utf-8").split(" ") if x.strip()]
    message_count = len(msg_ids)
    if message_count == 0:
        return message_count

    # Sanity check amount of messages that will be deleted
    assert message_count < sanity_check

    # Mark as deleted
    status, response = mailbox.store(",".join(msg_ids), "+FLAGS", "(\\Deleted)")
    assert status == "OK"

    if expunge:
        # Expunge to really delete
        status, response = mailbox.expunge()
        assert status == "OK"

    mailbox.close()

    return message_count


def retrieve_mail_by_message_id(
    mailbox: Union[imaplib.IMAP4_SSL, imaplib.IMAP4],
    message_id: str,
) -> bytes:
    status, count = mailbox.select("Inbox")
    # find message by message-id
    status, [msg_ids] = mailbox.search(
        None, 'HEADER "Message-Id" "{message_id}"'.format(message_id=message_id.strip())
    )
    messages = msg_ids.split()
    assert len(messages) <= 1
    if not messages:
        return None

    status, data = mailbox.fetch(messages[0], "(BODY[] UID)")
    assert status == "OK"
    mailbox.close()
    return data[0][1]


def unflag_mail(mailbox, uid):
    status, count = mailbox.select("Inbox")
    mailbox.uid("STORE", uid, "-FLAGS", "\\Flagged")
    mailbox.close()


def make_address(email: str, name: Optional[str] = None):
    if name:
        return '"%s" <%s>' % (name.replace('"', ""), email)
    return email


class UnsupportedMailFormat(Exception):
    pass


def get_bounce_headers(msgobj) -> dict[str, list[str]]:
    from .email_parsing import parse_header_field

    headers = defaultdict(list)
    for part in msgobj.walk():
        for k, v in part.items():
            if k in BOUNCE_HEADERS:
                headers[k].append(parse_header_field(v))
    return headers


def get_bounce_info(body, msgobj=None, date=None) -> BounceResult:
    headers = {}
    if msgobj is not None:
        headers = get_bounce_headers(msgobj)

    status = find_bounce_status(headers, body)

    diagnostic_code = headers.get("Diagnostic-Code", [None])[0]
    diagnostic_status = find_status_from_diagnostic(diagnostic_code)
    if status.is_more_expressive(diagnostic_status):
        status = diagnostic_status
    return status.to_bounce_result(diagnostic_code=diagnostic_code, date=date)


def find_bounce_status(headers, body=None) -> SmtpStatus:
    if match := SMTP_FULL_STATUS_RE.search(body):
        return SmtpStatus(
            SmtpBasicStatus.from_string(match.group(1)),
            SmtpExtendedStatus.from_string(match.group(2)),
        )

    extended_status = None
    for v in headers.get("Status", []):
        if match := SMTP_EXTENDED_STATUS_RE.match(v.strip()):
            extended_status = SmtpExtendedStatus.from_string(match.group(1))
            break

    if extended_status is None and body is not None:
        bounce_matches = len(set(BOUNCE_TEXT.findall(body)))
        if bounce_matches >= BOUNCE_TEXT_THRESHOLD:
            # Declare a Generic Error
            extended_status = SmtpExtendedStatus(5, 5, 0)
    return SmtpStatus(None, extended_status)


def find_status_from_diagnostic(
    message: str,
) -> SmtpStatus:
    if not message:
        return SmtpStatus(None, None)
    message = str(message)
    if match := SMTP_FULL_STATUS_RE.search(message):
        return SmtpStatus(
            SmtpBasicStatus.from_string(match.group(1)),
            SmtpExtendedStatus.from_string(match.group(2)),
        )

    basic_status = None
    if match := SMTP_DIAGNOSTIC_STATUS_RE.search(message):
        basic_status = SmtpBasicStatus.from_string(match.group(1))

    extended_status = None
    if match := SMTP_EXTENDED_STATUS_RE.search(message):
        extended_status = SmtpExtendedStatus.from_string(match.group(1))

    return SmtpStatus(basic_status, extended_status)


def detect_auto_reply(from_field, subject="", msgobj=None):
    if msgobj:
        for header, val in AUTO_REPLY_HEADERS:
            header_val = msgobj.get(header, None)
            if header_val is None:
                continue
            if val is None or val in header_val:
                return True

    if from_field and AUTO_REPLY_EMAIL_REGEX is not None:
        if AUTO_REPLY_EMAIL_REGEX.search(from_field[0]):
            return True

    if subject and AUTO_REPLY_SUBJECT_REGEX is not None:
        if AUTO_REPLY_SUBJECT_REGEX.search(subject) is not None:
            return True

    return False


SPF_MATCH = re.compile(r"\sspf=(\w+);?\s")


def check_spf(msgobj: EmailMessage) -> Optional[AuthenticityStatus]:
    spf_headers = msgobj.get_all("Received-SPF", [])
    if spf_headers:
        header = spf_headers[0]
        status = header.split(" ", 1)[0]
    else:
        auth_headers = msgobj.get_all("Authentication-Results", [])
        spf_headers = [h for h in auth_headers if SPF_MATCH.search(h) is not None]
        if not spf_headers:
            return
        header = spf_headers[0]
        match = SPF_MATCH.search(header)
        status = match.group(1)

    return AuthenticityStatus(
        check=AuthenticityCheck.SPF,
        status=status,
        failed=status.lower() == "fail" or status.lower() == "softfail",
        details=header,
    )


DMARC_MATCH = re.compile(r"\sdmarc=(\w+);?\s")


def check_dmarc(msgobj: EmailMessage) -> Optional[AuthenticityStatus]:
    auth_headers = msgobj.get_all("Authentication-Results", [])
    dmarc_headers = [h for h in auth_headers if DMARC_MATCH.search(h) is not None]
    if not dmarc_headers:
        return
    header = dmarc_headers[0]
    match = DMARC_MATCH.search(header)
    status = match.group(1)
    return AuthenticityStatus(
        check=AuthenticityCheck.DMARC,
        status=status,
        failed=status.lower() == "fail",
        details=header,
    )


DKIM_MATCH = re.compile(r"\sdkim=(\w+);?\s")


def check_dkim(msgobj: EmailMessage) -> Optional[AuthenticityStatus]:
    auth_headers = msgobj.get_all("Authentication-Results", [])
    dkim_headers = [h for h in auth_headers if DKIM_MATCH.search(h) is not None]
    if not dkim_headers:
        return
    header = dkim_headers[0]
    match = DKIM_MATCH.search(header)
    status = match.group(1)
    return AuthenticityStatus(
        check=AuthenticityCheck.DKIM,
        status=status,
        failed=status.lower() == "fail",
        details=header,
    )
