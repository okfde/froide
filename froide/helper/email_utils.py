"""

Original EmailParser Code by Ian Lewis:
http://www.ianlewis.org/en/parsing-email-attachments-python
Licensed under MIT

"""
from datetime import datetime
import time
from StringIO import StringIO
from email.Header import decode_header
from email.Parser import Parser
from email.utils import parseaddr, parsedate_tz, getaddresses

import imaplib

def get_unread_mails(host, port, user, password):
    mail = imaplib.IMAP4_SSL(host, port)
    mail.login(user, password)
    try:
        status, count = mail.select('Inbox')
        typ, data = mail.search(None, 'UNSEEN')
        for num in data[0].split():
            status, data = mail.fetch(num, '(RFC822)')
            yield data[0][1]
    finally:
        mail.close()
        mail.logout()

class UnsupportedMailFormat(Exception):
    pass

class EmailParser(object):

    def parse_attachment(self, message_part):
        content_disposition = message_part.get("Content-Disposition", None)
        if content_disposition:
            dispositions = content_disposition.strip().split(";")
            if content_disposition and dispositions[0].lower() == "attachment":
                file_data = message_part.get_payload(decode=True)
                attachment = StringIO(file_data)
                attachment.content_type = message_part.get_content_type()
                attachment.size = len(file_data)
                attachment.name = None
                attachment.create_date = None
                attachment.mod_date = None
                attachment.read_date = None

                for param in dispositions[1:]:
                    name,value = param.split("=")
                    name = name.lower()

                    if name == "filename":
                        attachment.name = value
                    elif name == "create-date":
                        attachment.create_date = value  #TODO: datetime
                    elif name == "modification-date":
                        attachment.mod_date = value #TODO: datetime
                    elif name == "read-date":
                        attachment.read_date = value #TODO: datetime
                return attachment
        return None

    def parse_date(self, date):
        date = parsedate_tz(date)
        if date is None:
            return None
        return (datetime.fromtimestamp(time.mktime(date[:9])), date[9])

    def parse(self, content):
        p = Parser()
        msgobj = p.parsestr(content)
        if msgobj['Subject'] is not None:
            decodefrag = decode_header(msgobj['Subject'])
            subj_fragments = []
            for s , enc in decodefrag:
                if enc:
                    s = unicode(s , enc).encode('utf8','replace')
                subj_fragments.append(s)
            subject = ''.join(subj_fragments)
        else:
            subject = None
        subject = subject.replace('\n\t', " ")
        attachments = []
        body = None
        html = None
        for part in msgobj.walk():
            attachment = self.parse_attachment(part)
            if attachment:
                attachments.append(attachment)
            elif part.get_content_type() == "text/plain":
                if body is None:
                    body = ""
                charset = part.get_content_charset() or 'ascii'
                body += unicode(
                    part.get_payload(decode=True),
                    charset,
                    'replace').encode('utf8','replace')
            elif part.get_content_type() == "text/html":
                if html is None:
                    html = ""
                charset = part.get_content_charset() or 'ascii'
                html += unicode(
                    part.get_payload(decode=True),
                    charset,
                    'replace').encode('utf8','replace')
        tos = getaddresses(msgobj.get_all('To', []))
        ccs = getaddresses(msgobj.get_all('Cc', []))
        resent_tos = getaddresses(msgobj.get_all('resent-to', []))
        resent_ccs = getaddresses(msgobj.get_all('resent-cc', []))
        date = self.parse_date(msgobj.get("Date"))
        return {
            'msgobj': msgobj,
            'date': date,
            'subject': subject,
            'body': body,
            'html': html,
            'from': parseaddr(msgobj.get('From')),
            'to': tos,
            'cc': ccs,
            'resent_to': resent_tos,
            'resent_cc': resent_ccs,
            'attachments': attachments
        }

 # uses the email flatten
 #        out_file = StringIO.StringIO()
 #        message_gen = Generator(out_file, mangle_from_=False, maxheaderlen=60)
 #        message_gen.flatten(message)
 #        message_text = out_file.getvalue()

 #        fixes mime encoding issues (for display within html)
 #        clean_text = quopri.decodestring(message_text)

