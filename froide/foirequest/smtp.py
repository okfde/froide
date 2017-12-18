import smtplib

from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
from django.core.mail.message import sanitize_address


class FoiEmailBackend(EmailBackend):
    RCPT_OPTIONS = ['NOTIFY=SUCCESS,DELAY,FAILURE']

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        encoding = email_message.encoding or settings.DEFAULT_CHARSET
        from_email = sanitize_address(email_message.from_email, encoding)
        recipients = [sanitize_address(addr, encoding) for addr in email_message.recipients()]
        message = email_message.message()
        try:
            self.connection.sendmail(from_email, recipients,
                                     message.as_bytes(linesep='\r\n'),
                                     rcpt_options=self.RCPT_OPTIONS)
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise
            return False
        return True
