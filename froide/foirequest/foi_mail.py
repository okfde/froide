import base64
import json
import zipfile
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import get_connection, EmailMessage, mail_managers
from django.core.urlresolvers import reverse
from django.utils.translation import override, ugettext, ugettext_lazy as _
from django.utils.six import BytesIO, string_types

from froide.helper.email_utils import (EmailParser, get_unread_mails,
                                       make_address)


unknown_foimail_message = _('''We received an FoI mail to this address: %(address)s.
No corresponding request could be identified, please investigate!
%(url)s
''')


def send_foi_mail(subject, message, from_email, recipient_list,
                  attachments=None, fail_silently=False, **kwargs):
    connection = get_connection(
        backend=getattr(settings, 'FOI_EMAIL_BACKEND', settings.EMAIL_BACKEND),
        username=settings.FOI_EMAIL_HOST_USER,
        password=settings.FOI_EMAIL_HOST_PASSWORD,
        host=settings.FOI_EMAIL_HOST,
        port=settings.FOI_EMAIL_PORT,
        use_tls=settings.FOI_EMAIL_USE_TLS,
        fail_silently=fail_silently
    )
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
    if attachments is not None:
        for name, data, mime_type in attachments:
            email.attach(name, data, mime_type)
    return email.send()


def _process_mail(mail_string, mail_type=None):
    parser = EmailParser()
    if mail_type is None:
        email = parser.parse(BytesIO(mail_string))
    elif mail_type == 'postmark':
        email = parser.parse_postmark(json.loads(mail_string.decode('utf-8')))
    return _deliver_mail(email, mail_string=mail_string)


def _deliver_mail(email, mail_string=None):
    from .models import FoiRequest, DeferredMessage

    received_list = email['to'] + email['cc'] \
            + email['resent_to'] + email['resent_cc']
            # TODO: BCC?

    domains = settings.FOI_EMAIL_DOMAIN
    if isinstance(domains, string_types):
        domains = [domains]

    mail_filter = lambda x: x[1].endswith(tuple(["@%s" % d for d in domains]))
    received_list = [r for r in received_list if mail_filter(r)]

    # normalize to first FOI_EMAIL_DOMAIN
    received_list = [(x[0], '@'.join(
        (x[1].split('@')[0], domains[0]))) for x in received_list]

    if mail_string is not None:
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
        try:
            foi_request = FoiRequest.objects.get_by_secret_mail(secret_mail)
        except FoiRequest.DoesNotExist:
            try:
                deferred = DeferredMessage.objects.get(recipient=secret_mail, request__isnull=False)
                foi_request = deferred.request
            except DeferredMessage.DoesNotExist:
                if mail_string is not None:
                    if not b64_encoded:
                        mail_string = base64.b64encode(mail_string.encode('utf-8')).decode("utf-8")
                DeferredMessage.objects.create(
                    recipient=secret_mail,
                    mail=mail_string,
                )
                with override(settings.LANGUAGE_CODE):
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


def package_foirequest(foirequest):
    zfile_obj = BytesIO()
    with override(settings.LANGUAGE_CODE):
        zfile = zipfile.ZipFile(zfile_obj, 'w')
        last_date = None
        date_count = 1
        for message in foirequest.messages:
            current_date = message.timestamp.date()
            date_prefix = current_date.isoformat()
            if current_date == last_date:
                date_count += 1
            else:
                date_count = 1
            date_prefix += '_%d' % date_count
            last_date = current_date

            att_queryset = message.foiattachment_set.filter(
                is_redacted=False,
                is_converted=False
            )
            if message.is_response:
                filename = '%s_%s.txt' % (date_prefix, ugettext('publicbody'))
            else:
                filename = '%s_%s.txt' % (date_prefix, ugettext('requester'))

            zfile.writestr(filename, message.get_formated(att_queryset).encode('utf-8'))

            for attachment in att_queryset:
                filename = '%s-%s' % (date_prefix, attachment.name)
                zfile.write(attachment.file.path, arcname=filename)
        zfile.close()
    return zfile_obj.getvalue()
