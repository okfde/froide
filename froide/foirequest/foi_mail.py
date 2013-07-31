import base64
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import get_connection, EmailMessage, mail_managers
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from froide.helper.email_utils import (EmailParser, get_unread_mails, make_address)


unknown_foimail_message = _('''We received an FoI mail to this address: %(address)s.
No corresponding request could be identified, please investigate!
%(url)s
''')


def send_foi_mail(subject, message, from_email, recipient_list,
              fail_silently=False, **kwargs):
    connection = get_connection(username=settings.FOI_EMAIL_HOST_USER,
            password=settings.FOI_EMAIL_HOST_PASSWORD,
            host=settings.FOI_EMAIL_HOST,
            port=settings.FOI_EMAIL_PORT,
            use_tls=settings.FOI_EMAIL_USE_TLS,
            fail_silently=fail_silently)
    headers = {}
    if "message_id" in kwargs:
        headers['Message-ID'] = kwargs.pop("message_id")
    if settings.FOI_EMAIL_FIXED_FROM_ADDRESS:
        name, mailaddr = parseaddr(from_email)
        from_address = settings.FOI_EMAIL_HOST_FROM
        from_email = make_address(from_address, name)
        headers['Reply-To'] = make_address(mailaddr, name)
    else:
        headers['Reply-To'] = from_email
    email = EmailMessage(subject, message, from_email, recipient_list,
                        connection=connection, headers=headers)
    return email.send()


def _process_mail(mail_string):
    from .models import FoiRequest, DeferredMessage

    parser = EmailParser()
    email = parser.parse(mail_string)
    received_list = email['to'] + email['cc'] \
            + email['resent_to'] + email['resent_cc']
            # TODO: BCC?
    mail_filter = lambda x: x[1].endswith("@%s" % settings.FOI_EMAIL_DOMAIN)
    received_list = filter(mail_filter, received_list)

    # make original mail storeable as unicode
    b64_encoded = False
    try:
        mail_string = mail_string.decode("utf-8")
    except UnicodeDecodeError:
        b64_encoded = True
        mail_string = base64.b64encode(mail_string).decode("utf-8")

    already = set()
    for received in received_list:
        secret_mail = received[1]
        if secret_mail in already:
            continue
        already.add(secret_mail)
        if not secret_mail.endswith('@%s' % settings.FOI_EMAIL_DOMAIN):
            continue
        try:
            foi_request = FoiRequest.objects.get_by_secret_mail(secret_mail)
        except FoiRequest.DoesNotExist:
            try:
                deferred = DeferredMessage.objects.get(recipient=secret_mail, request__isnull=False)
                foi_request = deferred.request
            except DeferredMessage.DoesNotExist:
                if not b64_encoded:
                    mail_string = base64.b64encode(mail_string).decode("utf-8")
                DeferredMessage.objects.create(
                    recipient=secret_mail,
                    mail=mail_string,
                )
                mail_managers(_('Unknown FoI-Mail Recipient'),
                    unknown_foimail_message % {
                        'address': secret_mail,
                        'url': settings.SITE_URL + reverse('admin:foirequest_deferredmessage_changelist')
                    }
                )
                continue
        foi_request.add_message_from_email(email, mail_string)


def _fetch_mail():
    for rfc_data in get_unread_mails(settings.FOI_EMAIL_HOST_IMAP,
            settings.FOI_EMAIL_PORT_IMAP,
            settings.FOI_EMAIL_ACCOUNT_NAME,
            settings.FOI_EMAIL_ACCOUNT_PASSWORD,
            ssl=settings.FOI_EMAIL_USE_SSL):
        yield rfc_data


def fetch_and_process():
    count = 0
    for rfc_data in _fetch_mail():
        _process_mail(rfc_data)
        count += 1
    return count
