import contextlib
import imaplib
import re
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from email.message import EmailMessage
from enum import Enum
from typing import Iterator, Optional, Tuple, Union

from django.conf import settings
from django.utils import timezone

AUTO_REPLY_SUBJECT_REGEX = settings.FROIDE_CONFIG.get("auto_reply_subject_regex", None)
AUTO_REPLY_EMAIL_REGEX = settings.FROIDE_CONFIG.get("auto_reply_email_regex", None)
AUTO_REPLY_HEADERS = (
    ("X-Autoreply", None),
    ("X-Autorespond", None),
    ("Auto-Submitted", "auto-replied"),
)
BOUNCE_STATUS_RE = re.compile(r"(\d\.\d+\.\d+)", re.IGNORECASE)
BOUNCE_DIAGNOSTIC_STATUS_RE = re.compile(r"smtp; (\d{3})")
BOUNCE_TEXT = re.compile(
    r"""5\d{2}\ Requested\ action\ not\ taken |
RESOLVER\.ADR\.RecipNotFound |
mailbox\ unavailable |
RCPT\ TO\ command |
permanent\ error |
SMTP\ error |
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
    "Received",
    "Remote-Mta",
    "Remote-MTA",
    "Reporting-MTA",
    "Reporting-Mta",
    "Status",
)

DsnStatus = namedtuple("DsnStatus", "class_ subject detail")


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


BounceResult = namedtuple(
    "BounceResult", "status is_bounce bounce_type diagnostic_code timestamp"
)

GENERIC_ERROR = DsnStatus(5, 0, 0)
MAILBOX_FULL = DsnStatus(5, 2, 2)

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
        None, 'HEADER "Message-Id" "{message_id}"'.format(message_id=message_id)
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


def make_address(email, name=None):
    if name:
        return '"%s" <%s>' % (name.replace('"', ""), email)
    return email


class UnsupportedMailFormat(Exception):
    pass


def get_bounce_headers(msgobj):
    headers = defaultdict(list)
    for part in msgobj.walk():
        for k, v in part.items():
            if k in BOUNCE_HEADERS:
                headers[k].append(v)
    return headers


def get_bounce_info(body, msgobj=None, date=None):
    headers = {}
    if msgobj is not None:
        headers = get_bounce_headers(msgobj)
    status = find_bounce_status(headers, body)
    diagnostic_code = headers.get("Diagnostic-Code", [None])[0]
    diagnostic_status = find_status_from_diagnostic(diagnostic_code)
    if status == GENERIC_ERROR and diagnostic_status != status:
        status = diagnostic_status
    bounce_type = classify_bounce_status(status)
    return BounceResult(
        status=status,
        bounce_type=bounce_type,
        is_bounce=bool(bounce_type),
        diagnostic_code=diagnostic_code,
        timestamp=date or timezone.now(),
    )


def find_bounce_status(headers, body=None):
    for v in headers.get("Status", []):
        match = BOUNCE_STATUS_RE.match(v.strip())
        if match is not None:
            return DsnStatus(*[int(x) for x in match.group(1).split(".")])

    if body is not None:
        bounce_matches = len(BOUNCE_TEXT.findall(body))
        if bounce_matches >= BOUNCE_TEXT_THRESHOLD:
            # Declare a DSN status of 5.5.0
            return DsnStatus(5, 5, 0)
    return None


def find_status_from_diagnostic(message):
    if not message:
        return
    message = str(message)
    match = BOUNCE_DIAGNOSTIC_STATUS_RE.search(message)
    if match is None:
        match = BOUNCE_STATUS_RE.search(message)
        if match is None:
            return
        return DsnStatus(*[int(x) for x in match.group(1).split(".")])
    return DsnStatus(*[int(x) for x in match.group(1)])


def classify_bounce_status(status):
    if status is None:
        return
    if status.class_ == 2:
        return
    if status.class_ == 4:
        return "soft"
    # Mailbox full should be treated as a temporary problem
    if status == MAILBOX_FULL:
        return "soft"
    if status.class_ == 5:
        return "hard"


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


def check_spf(msgobj: EmailMessage) -> Optional[AuthenticityStatus]:
    spf_headers = msgobj.get_all("Received-SPF", [])
    if not spf_headers:
        return
    header = spf_headers[0]
    status = header.split(" ", 1)[0]
    return AuthenticityStatus(
        check=AuthenticityCheck.SPF,
        status=status,
        failed=status.lower() == "fail",
        details=header,
    )


DMARC_MATCH = re.compile(r"\sdmarc=(\w+)\s")


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


DKIM_MATCH = re.compile(r"\sdkim=(\w+)\s")


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
