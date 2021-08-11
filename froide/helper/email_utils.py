"""

Original EmailParser Code by Ian Lewis:
http://www.ianlewis.org/en/parsing-email-attachments-python
Licensed under MIT

"""

from collections import namedtuple
import contextlib
from io import BytesIO
import base64
import re
from email.parser import BytesParser as Parser
import imaplib
from typing import Iterator, Tuple, Optional, Union

from django.conf import settings
from django.utils import timezone
from django.utils.functional import cached_property

from .text_utils import convert_html_to_text
from .email_parsing import (
    parse_email_body, parse_main_headers, parse_date, get_bounce_headers
)


AUTO_REPLY_SUBJECT_REGEX = settings.FROIDE_CONFIG.get(
    'auto_reply_subject_regex', None)
AUTO_REPLY_EMAIL_REGEX = settings.FROIDE_CONFIG.get(
    'auto_reply_email_regex', None)
AUTO_REPLY_HEADERS = (
    ('X-Autoreply', None),
    ('X-Autorespond', None),
    ('Auto-Submitted', 'auto-replied'),
)
BOUNCE_STATUS_RE = re.compile(r'(\d\.\d+\.\d+)', re.IGNORECASE)
BOUNCE_DIAGNOSTIC_STATUS_RE = re.compile(r'smtp; (\d{3})')
BOUNCE_TEXT = re.compile(r'''5\d{2}\ Requested\ action\ not\ taken |
RESOLVER\.ADR\.RecipNotFound |
mailbox\ unavailable |
RCPT\ TO\ command |
permanent\ error |
SMTP\ error |
original\ message |
Return-Path:\ # If headers are given in verbose
''', re.X | re.I)
BOUNCE_TEXT_THRESHOLD = 3  # At least three occurences of above patterns

DsnStatus = namedtuple('DsnStatus', 'class_ subject detail')

BounceResult = namedtuple('BounceResult', 'status is_bounce bounce_type diagnostic_code timestamp')

GENERIC_ERROR = DsnStatus(5, 0, 0)
MAILBOX_FULL = DsnStatus(5, 2, 2)

# Restrict to max 3 consecutive newlines in email body
MULTI_NL_RE = re.compile('((?:\r?\n){,3})(?:\r?\n)*')
UID_RE = re.compile(r'UID\s+(?P<uid>\d+)')


def get_imap_message_uid(flag_bytes):
    match = UID_RE.search(flag_bytes.decode())
    if match is None:
        return None
    return match.group('uid')


@contextlib.contextmanager
def get_mail_client(host, port, user, password, ssl=True):
    klass = imaplib.IMAP4
    if ssl:
        klass = imaplib.IMAP4_SSL
    con = klass(host, port)
    con.login(user, password)

    yield con

    con.close()
    con.logout()


def get_unread_mails(
        mailbox: Union[imaplib.IMAP4_SSL, imaplib.IMAP4],
        flag=False) -> Iterator[Tuple[Optional[str], bytes]]:
    status, count = mailbox.select('Inbox')
    typ, data = mailbox.search(None, 'UNSEEN')
    for num in data[0].split():
        status, data = mailbox.fetch(num, '(BODY[] UID)')
        uid = get_imap_message_uid(data[0][0])
        if flag:
            mailbox.store(num, '+FLAGS', '\\Flagged')
        yield uid, data[0][1]


def delete_mails_by_recipient(
        mailbox: Union[imaplib.IMAP4_SSL, imaplib.IMAP4],
        recipient_mail: str,
        expunge=False, sanity_check=100) -> int:
    '''
    Delete all mail to recipient_mail in IMAP mailbox
    '''
    assert recipient_mail

    status, count = mailbox.select('Inbox')
    # find all messages to recipient mail
    status, [msg_ids] = mailbox.search(
        None,
        '(OR TO "{recipient}" CC "{recipient}")'.format(
            recipient=recipient_mail
        )
    )
    msg_ids = [x.strip() for x in msg_ids.decode('utf-8').split(' ') if x.strip()]
    message_count = len(msg_ids)
    if message_count == 0:
        return message_count

    # Sanity check amount of messages that will be deleted
    assert message_count < sanity_check

    # Mark as deleted
    status, response = mailbox.store(','.join(msg_ids), '+FLAGS', '(\\Deleted)')
    assert status == 'OK'

    if expunge:
        # Expunge to really delete
        status, response = mailbox.expunge()
        assert status == 'OK'

    return message_count


def unflag_mail(mailbox, uid):
    status, count = mailbox.select('Inbox')
    mailbox.uid('STORE', uid, '-FLAGS', '\\Flagged')


def make_address(email, name=None):
    if name:
        return '"%s" <%s>' % (name.replace('"', ''), email)
    return email


class UnsupportedMailFormat(Exception):
    pass


def find_bounce_status(headers, body=None):
    for v in headers.get('Status', []):
        match = BOUNCE_STATUS_RE.match(v.strip())
        if match is not None:
            return DsnStatus(*[int(x) for x in match.group(1).split('.')])

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
        return DsnStatus(*[int(x) for x in match.group(1).split('.')])
    return DsnStatus(*[int(x) for x in match.group(1)])


def classify_bounce_status(status):
    if status is None:
        return
    if status.class_ == 2:
        return
    if status.class_ == 4:
        return 'soft'
    # Mailbox full should be treated as a temporary problem
    if status == MAILBOX_FULL:
        return 'soft'
    if status.class_ == 5:
        return 'hard'


class ParsedEmail(object):
    message_id = None
    date = None

    def __init__(self, msgobj, **kwargs):
        self.msgobj = msgobj
        for k, v in kwargs.items():
            setattr(self, k, v)

    @cached_property
    def bounce_info(self):
        return self.get_bounce_info()

    def get_bounce_info(self):
        headers = {}
        if self.msgobj is not None:
            headers = get_bounce_headers(self.msgobj)
        status = find_bounce_status(headers, self.body)
        diagnostic_code = headers.get('Diagnostic-Code', [None])[0]
        diagnostic_status = find_status_from_diagnostic(diagnostic_code)
        if status == GENERIC_ERROR and diagnostic_status != status:
            status = diagnostic_status
        bounce_type = classify_bounce_status(status)
        return BounceResult(
            status=status,
            bounce_type=bounce_type,
            is_bounce=bool(bounce_type),
            diagnostic_code=diagnostic_code,
            timestamp=self.date or timezone.now()
        )

    @cached_property
    def is_auto_reply(self):
        return self.detect_auto_reply()

    def detect_auto_reply(self):
        msgobj = self.msgobj
        if msgobj:
            for header, val in AUTO_REPLY_HEADERS:
                header_val = msgobj.get(header, None)
                if header_val is None:
                    continue
                if val is None or val in header_val:
                    return True

        from_field = self.from_
        if from_field and AUTO_REPLY_EMAIL_REGEX is not None:
            if AUTO_REPLY_EMAIL_REGEX.search(from_field[0]):
                return True

        subject = self.subject
        if subject and AUTO_REPLY_SUBJECT_REGEX is not None:
            if AUTO_REPLY_SUBJECT_REGEX.search(subject) is not None:
                return True

        return False

    def is_direct_recipient(self, email_address):
        return any(
            email.lower() == email_address.lower() for name, email in self.to
        )


def fix_email_body(body):
    return MULTI_NL_RE.sub('\\1', body)


class EmailParser(object):

    def parse(self, bytesfile):
        p = Parser()
        msgobj = p.parse(bytesfile)

        body, html, attachments = parse_email_body(msgobj)
        body = '\n'.join(body).strip()
        html = '\n'.join(html).strip()

        if not body and html:
            body = convert_html_to_text(html)

        body = fix_email_body(body)

        email_info = parse_main_headers(msgobj)
        email_info.update({
            'body': body,
            'html': html,
            'attachments': attachments
        })

        return ParsedEmail(msgobj, **email_info)

    def parse_postmark(self, obj):
        from_field = (obj['FromFull']['Name'], obj['FromFull']['Email'])
        tos = [(o['Name'], o['Email']) for o in obj['ToFull']]
        ccs = [(o['Name'], o['Email']) for o in obj['CcFull']]
        attachments = []
        for a in obj['Attachments']:
            attachment = BytesIO(base64.b64decode(a['Content']))
            attachment.content_type = a['ContentType']
            attachment.size = a['ContentLength']
            attachment.name = a['Name']
            attachment.create_date = None
            attachment.mod_date = None
            attachment.read_date = None
            attachments.append(attachment)

        return ParsedEmail(None, **{
            'postmark_msgobj': obj,
            'date': parse_date(obj['Date']),
            'subject': obj['Subject'],
            'body': obj['TextBody'],
            'html': obj['HtmlBody'],
            'from_': from_field,
            'to': tos,
            'cc': ccs,
            'resent_to': [],
            'resent_cc': [],
            'attachments': attachments
        })
