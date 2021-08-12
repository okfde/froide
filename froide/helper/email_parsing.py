"""

Original EmailParser Code by Ian Lewis:
http://www.ianlewis.org/en/parsing-email-attachments-python
Licensed under MIT

"""

import base64
import re
import time
from contextlib import closing
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import EmailMessage
from email.parser import BytesParser as Parser
from email.utils import getaddresses, parseaddr, parsedate_tz
from io import BytesIO
from typing import List, Optional, Tuple
from urllib.parse import unquote

import pytz
from django.utils.functional import cached_property

from .text_utils import convert_html_to_text
from .email_utils import get_bounce_info, detect_auto_reply

# Restrict to max 3 consecutive newlines in email body
MULTI_NL_RE = re.compile("((?:\r?\n){,3})(?:\r?\n)*")

DISPO_SPLIT = re.compile(r"""((?:[^;"']|"[^"]*"|'[^']*')+)""")
# Reassemble regular-parameter section
# https://tools.ietf.org/html/rfc2231#7
DISPO_MULTI_VALUE = re.compile(r"(\w+)\*\d+$")


def split_with_quotes(dispo):
    return [x.strip() for x in DISPO_SPLIT.split(dispo.strip()) if x and x != ";"]


def get_email_headers(message_bytes, headers=None):
    p = Parser()
    with closing(BytesIO(message_bytes)) as stream:
        msgobj = p.parse(stream)
    if headers is None:
        headers = dict(msgobj)
    return {k: [parse_header_field(x) for x in msgobj.get_all(k, [])] for k in headers}


class EmailAttachment(BytesIO):
    content_type: str
    size: int
    name: Optional[str]
    create_date: Optional[str]
    mod_date: Optional[str]
    read_date: Optional[str]


def parse_email_body(
    msgobj: EmailMessage,
) -> Tuple[List[str], List[str], List[EmailAttachment]]:
    body = []
    html = []
    attachments = []
    for part in msgobj.walk():
        attachment = parse_attachment(part)
        if attachment:
            attachments.append(attachment)
        elif part.get_content_type() == "text/plain":
            body.append(decode_message_part(part))
        elif part.get_content_type() == "text/html":
            html.append(decode_message_part(part))
    return body, html, attachments


def decode_message_part(part):
    charset = part.get_content_charset() or "ascii"
    return str(part.get_payload(decode=True), charset, "replace")


def parse_main_headers(msgobj):
    subject = parse_header_field(msgobj["Subject"])
    tos = get_address_list(msgobj.get_all("To", []))
    tos.extend(get_address_list(msgobj.get_all("X-Original-To", [])))
    ccs = get_address_list(msgobj.get_all("Cc", []))
    resent_tos = get_address_list(msgobj.get_all("resent-to", []))
    resent_ccs = get_address_list(msgobj.get_all("resent-cc", []))

    from_field = parseaddr(str(msgobj.get("From")))
    from_field = (
        parse_header_field(from_field[0]),
        from_field[1].lower() if from_field[1] else from_field[1],
    )
    date = parse_date(str(msgobj.get("Date")))
    return {
        "message_id": msgobj.get("Message-Id"),
        "date": date,
        "subject": subject,
        "from_": from_field,
        "to": tos,
        "cc": ccs,
        "resent_to": resent_tos,
        "resent_cc": resent_ccs,
    }


def parse_dispositions(dispo):
    if not isinstance(dispo, str):
        dispo = parse_header_field(dispo)
    dispos = split_with_quotes(dispo)
    dispo_name = dispos[0].lower()
    dispo_dict = {}
    for param in dispos[1:]:
        if "=" not in param:
            continue
        name, value = param.split("=", 1)
        name = name.lower().strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        multi_name = DISPO_MULTI_VALUE.match(name)
        if multi_name:
            name = multi_name.group(1)
            if name in dispo_dict:
                dispo_dict[name] += value
            else:
                dispo_dict[name] = value
        else:
            dispo_dict[name] = value

    for name, value in dispo_dict.items():
        dispo_dict[name] = parse_header_field(value)

    return dispo_name, dispo_dict


def parse_attachment(message_part):
    content_disposition = message_part.get("Content-Disposition", None)
    if not content_disposition:
        return None
    dispo_type, dispo_dict = parse_dispositions(content_disposition)
    if not (
        dispo_type == "attachment"
        or (dispo_type == "inline" and "filename" in dispo_dict)
    ):
        return None

    content_type = message_part.get("Content-Type", None)
    file_data = message_part.get_payload(decode=True)
    if file_data is None:
        payloads = message_part.get_payload()
        file_data = "\n\n".join([p.as_string() for p in payloads]).encode("utf-8")
    attachment = EmailAttachment(file_data)
    attachment.content_type = message_part.get_content_type()
    attachment.size = len(file_data)
    attachment.name = None
    attachment.create_date = None
    attachment.mod_date = None
    attachment.read_date = None
    attachment.name = get_attachment_name(
        attachment, dispo_dict, content_type=content_type
    )

    if "create-date" in dispo_dict:
        attachment.create_date = dispo_dict["create-date"]  # TODO: datetime
    if "modification-date" in dispo_dict:
        attachment.mod_date = dispo_dict["modification-date"]  # TODO: datetime
    if "read-date" in dispo_dict:
        attachment.read_date = dispo_dict["read-date"]  # TODO: datetime
    return attachment


def get_attachment_name(attachment, dispo_dict, content_type=None):
    name = None
    if "filename" in dispo_dict:
        name = dispo_dict["filename"]
    if name is None and "filename*" in dispo_dict:
        name = parse_extended_header_field(dispo_dict["filename*"])

    if content_type:
        _, content_dict = parse_dispositions(content_type)
        if "name" in content_dict:
            name = content_dict["name"]
        if name is None and "name*" in content_dict:
            name = parse_extended_header_field(content_dict["name*"])

    if name is None and content_type == "message/rfc822":
        attachment_bytes = attachment.getvalue()
        attachment_headers = get_email_headers(attachment_bytes, ["Subject"])
        subject = attachment_headers["Subject"]
        if subject:
            name = "%s.eml" % subject[0][:45]
    return name


def parse_header_field(field):
    if field is None:
        return None

    if isinstance(field, str):
        # For Python 2
        # see http://stackoverflow.com/questions/7331351/python-email-header-decoding-utf-8
        field = re.sub(r"(=\?[\w-]+\?\w\?.*\?=)(?!$)", r"\1 ", field)
        field = field.replace("\n  ", "")

    try:
        decodefrag = decode_header(field)
    except UnicodeEncodeError:
        # Python 2 failure
        if isinstance(field, str):
            return field
        return try_decoding(field)

    if decodefrag and isinstance(decodefrag[0][0], bytes) and b"=?" in decodefrag[0][0]:
        # Likely failed to decode!
        # Python expects encoded words in individual lines
        # https://github.com/python/cpython/blob/a8d5e2f255f1a20fc8af7dc16a7cb708e014952a/Lib/email/header.py#L86
        # But encoded words may have been split up!
        # Let's remove newlines that are not preceded by
        # encoded word terminator and try again
        field = re.sub(r"(?<!\?\=)\n ", "=20", field)
        decodefrag = decode_header(field)

    fragments = []
    for s, enc in decodefrag:
        decoded = None
        if enc or not isinstance(s, str):
            decoded = try_decoding(s, encoding=enc)
        else:
            decoded = s
        fragments.append(decoded.strip(" "))
    field = " ".join(fragments)
    return field.replace("\n\t", " ").replace("\n", "").replace("\r", "")


def parse_extended_header_field(field):
    """
    https://tools.ietf.org/html/rfc5987#section-3.2
    """
    try:
        fname_encoding, fname_lang, fname = field.split("'")
    except ValueError:
        return str(field)
    return unquote(fname, encoding=fname_encoding)


def try_decoding(encoded, encoding=None):
    decoded = None
    if encoding and encoding != "unknown-8bit":
        try:
            decoded = encoded.decode(encoding, errors="replace")
        except (UnicodeDecodeError, LookupError):
            pass
    if decoded is None:
        # Try common encodings
        for enc in ("utf-8", "latin1"):
            try:
                decoded = encoded.decode(enc)
                break
            except UnicodeDecodeError:
                continue
    if decoded is None:
        # Fall back to ascii and replace
        decoded = encoded.decode("ascii", errors="replace")
    return decoded


def get_address_list(values):
    values = [parse_header_field(value) for value in values]
    address_list = getaddresses(values)
    fixed = []
    for addr in address_list:
        fixed.append((parse_header_field(addr[0]), addr[1]))
    return fixed


def parse_date(date_str):
    date_tuple = parsedate_tz(date_str)
    if date_tuple is None:
        return None
    date = datetime.fromtimestamp(time.mktime(date_tuple[:9]))
    offset = date_tuple[9]
    if offset is not None:
        date = date - timedelta(seconds=offset)
    return pytz.utc.localize(date)


EmailField = Tuple[str, str]


class ParsedEmail(object):
    message_id: str = ""
    date: datetime = None
    subject: str
    body: str
    html: Optional[str]
    from_: EmailField
    to: List[EmailField]
    cc: List[EmailField]
    resent_to: List[EmailField]
    resent_cc: List[EmailField]
    attachments: List[EmailAttachment]

    def __init__(self, msgobj, **kwargs):
        self.msgobj = msgobj
        for k, v in kwargs.items():
            setattr(self, k, v)

    @cached_property
    def bounce_info(self):
        return self.get_bounce_info()

    def get_bounce_info(self):
        return get_bounce_info(self.body, msgobj=self.msgobj, date=self.date)

    @cached_property
    def is_auto_reply(self):
        return self.detect_auto_reply()

    def detect_auto_reply(self):
        return detect_auto_reply(self.from_, subject=self.subject, msgobj=self.msgobj)

    def is_direct_recipient(self, email_address):
        return any(email.lower() == email_address.lower() for name, email in self.to)


def fix_email_body(body):
    return MULTI_NL_RE.sub("\\1", body)


def parse_email(bytesfile: BytesIO) -> ParsedEmail:
    p = Parser()
    msgobj = p.parse(bytesfile)

    body, html, attachments = parse_email_body(msgobj)
    body = "\n".join(body).strip()
    html = "\n".join(html).strip()

    if not body and html:
        body = convert_html_to_text(html)

    body = fix_email_body(body)

    email_info = parse_main_headers(msgobj)
    email_info.update({"body": body, "html": html, "attachments": attachments})

    return ParsedEmail(msgobj, **email_info)


def parse_postmark(obj):
    from_field = (obj["FromFull"]["Name"], obj["FromFull"]["Email"])
    tos = [(o["Name"], o["Email"]) for o in obj["ToFull"]]
    ccs = [(o["Name"], o["Email"]) for o in obj["CcFull"]]
    attachments = []
    for a in obj["Attachments"]:
        attachment = BytesIO(base64.b64decode(a["Content"]))
        attachment.content_type = a["ContentType"]
        attachment.size = a["ContentLength"]
        attachment.name = a["Name"]
        attachment.create_date = None
        attachment.mod_date = None
        attachment.read_date = None
        attachments.append(attachment)

    return ParsedEmail(
        None,
        **{
            "postmark_msgobj": obj,
            "date": parse_date(obj["Date"]),
            "subject": obj["Subject"],
            "body": obj["TextBody"],
            "html": obj["HtmlBody"],
            "from_": from_field,
            "to": tos,
            "cc": ccs,
            "resent_to": [],
            "resent_cc": [],
            "attachments": attachments,
        }
    )
