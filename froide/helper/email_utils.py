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


def get_unread_mails(host, port, user, password, ssl=True):
    klass = imaplib.IMAP4
    if ssl:
        klass = imaplib.IMAP4_SSL
    mail = klass(host, port)
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


def make_address(email, name=None):
    if name:
        return "%s <%s>" % (name, email)
    return email


class UnsupportedMailFormat(Exception):
    pass


class EmailParser(object):

    def parse_dispositions(self, dispo):
        dispos = dispo.strip().split(";")
        dispo_name = dispos[0].lower()
        dispo_dict = {}
        for param in dispos[1:]:
            name, value = param.split("=", 1)
            name = name.lower().strip()
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            dispo_dict[name] = value
        return dispo_name, dispo_dict

    def parse_attachment(self, message_part):
        content_disposition = message_part.get("Content-Disposition", None)
        if content_disposition:
            dispo_type, dispo_dict = self.parse_dispositions(content_disposition)
            if dispo_type == "attachment" or (dispo_type == 'inline' and
                    'filename' in dispo_dict):
                file_data = message_part.get_payload(decode=True)
                if file_data is None:
                    file_data = ""
                attachment = StringIO(file_data)
                attachment.content_type = message_part.get_content_type()
                attachment.size = len(file_data)
                attachment.name = None
                attachment.create_date = None
                attachment.mod_date = None
                attachment.read_date = None

                if "filename" in dispo_dict:
                    attachment.name = dispo_dict['filename']
                elif "create-date" in dispo_dict:
                    attachment.create_date = dispo_dict['create-date']  # TODO: datetime
                elif "modification-date" in dispo_dict:
                    attachment.mod_date = dispo_dict['modification-date']  # TODO: datetime
                elif "read-date" in dispo_dict:
                    attachment.read_date = dispo_dict['read-date']  # TODO: datetime
                return attachment
        return None

    def parse_date(self, date):
        date = parsedate_tz(date)
        if date is None:
            return None
        return (datetime.fromtimestamp(time.mktime(date[:9])), date[9])

    def parse_body(self, parts, attachments, body, html):
        for part in parts:
            attachment = self.parse_attachment(part)
            if attachment:
                attachments.append(attachment)
            elif part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or 'ascii'
                body.append(unicode(
                    part.get_payload(decode=True),
                    charset, 'replace').encode('utf8', 'replace'))
            elif part.get_content_type() == "text/html":
                charset = part.get_content_charset() or 'ascii'
                html.append(unicode(
                    part.get_payload(decode=True),
                    charset,
                    'replace').encode('utf8', 'replace'))

    def parse(self, content):
        p = Parser()
        msgobj = p.parsestr(content)
        if msgobj['Subject'] is not None:
            decodefrag = decode_header(msgobj['Subject'])
            subj_fragments = []
            for s, enc in decodefrag:
                if enc:
                    try:
                        s = unicode(s, enc)
                    except UnicodeDecodeError:
                        # desperate move here
                        try:
                            s = s.decode("latin1")
                        except:
                            pass
                subj_fragments.append(s)
            subject = ''.join(subj_fragments)
            subject = subject.replace('\n\t', " ")
        else:
            subject = None
        attachments = []
        body = []
        html = []
        self.parse_body(msgobj.walk(), attachments, body, html)
        body = '\n'.join(body)
        html = '\n'.join(html)
        tos = getaddresses(msgobj.get_all('To', []))
        tos.extend(getaddresses(msgobj.get_all('X-Original-To', [])))
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

if __name__ == '__main__':
    p = EmailParser()
    email = p.parse(file('../foirequest/tests/test_mail_03.txt').read())
    for i, at in enumerate(email['attachments']):
        file(getattr(at, 'name', 'test'), 'w').write(at.read())
