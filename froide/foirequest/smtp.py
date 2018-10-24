import smtplib

from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend
from django.conf import settings
from django.core.mail.message import sanitize_address


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
        from_email = sanitize_address(email_message.from_email, encoding)
        from_email = self.return_path or from_email
        recipients = [sanitize_address(addr, encoding) for addr in email_message.recipients()]
        message = email_message.message()
        try:
            self.connection.sendmail(from_email, recipients,
                                     message.as_bytes(linesep='\r\n'),
                                     rcpt_options=self.rcpt_options)
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise
            return False
        return True
