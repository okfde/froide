import smtplib
import logging
import re

from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend
from django.conf import settings
from django.core.mail.message import sanitize_address

from froide.bounce.utils import handle_smtp_error

FIX_RE = re.compile(r'^([^"].*) <(.*)>$')

logger = logging.getLogger(__name__)


def fix_address(a):
    return FIX_RE.sub('"\\1" <\\2>', a)


class EmailBackend(DjangoEmailBackend):
    def __init__(self, **kwargs):
        self.rcpt_options = kwargs.pop('rcpt_options', [])
        self.return_path = kwargs.pop('return_path', None)
        super().__init__(**kwargs)

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        encoding = email_message.encoding or settings.DEFAULT_CHARSET
        email_message.from_email = fix_address(email_message.from_email)
        from_email = sanitize_address(email_message.from_email, encoding)
        from_email = self.return_path or from_email
        recipients = [sanitize_address(addr, encoding) for addr in email_message.recipients()]
        message = email_message.message()
        try:
            self.connection.sendmail(from_email, recipients,
                                     message.as_bytes(linesep='\r\n'),
                                     rcpt_options=self.rcpt_options)
        except smtplib.SMTPRecipientsRefused as e:
            handle_smtp_error(e)
            logger.exception(e)
            return False
        except smtplib.SMTPException as e:
            logger.exception(e)
            return False
        except Exception as e:
            logger.exception(e)
            return False
        return True
