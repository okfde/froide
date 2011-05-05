import logging

from django.conf import settings

from foirequest.models import FoiRequest
from froide.helper.email_utils import (EmailParser,
        UnsupportedMailFormat, get_unread_mails)

def _process_mail(mail_string):
    parser = EmailParser()
    try:
        email = parser.parse(mail_string)
    except UnsupportedMailFormat:
        logging.warn("Unsupported Mail Format: %s" % mail_string)
        return

    received_list = email['to'] + email['cc'] \
            + email['resent_to'] + email['resent_cc']
            # TODO: BCC?

    mail_filter = lambda x: x[1].endswith("@%s" % settings.FOI_MAIL_DOMAIN)
    received_list = filter(mail_filter, received_list)
    for received in received_list:
        secret_mail = received[1]
        try:
            foi_request = FoiRequest.objects.get_by_secret_mail(secret_mail)
        except FoiRequest.DoesNotExist:
            continue
        foi_request.add_message_from_email(email, mail_string)

def _fetch_mail():
    for rfc_data in get_unread_mails(settings.FOI_MAIL_HOST,
            settings.FOI_MAIL_PORT,
            settings.FOI_MAIL_ACCOUNT_NAME,
            settings.FOI_MAIL_ACCOUNT_PASSWORD):
        yield rfc_data

def fetch_and_process():
    count = 0
    for rfc_data in _fetch_mail():
        _process_mail(rfc_data)
        count += 1
    return count
