import base64
import json
import zipfile
from email.utils import parseaddr
import random

from django.conf import settings
from django.core.mail import get_connection, EmailMessage, mail_managers
from django.core.urlresolvers import reverse
from django.utils.translation import override, ugettext, ugettext_lazy as _
from django.utils.six import BytesIO, string_types

from froide.helper.email_utils import (EmailParser, get_unread_mails,
                                       make_address)
from froide.helper.name_generator import get_name_from_number


unknown_foimail_message = _('''We received an FoI mail to this address: %(address)s.
No corresponding request could be identified, please investigate! %(url)s
''')

spam_message = _('''We received a possible spam mail to this address: %(address)s.
Please investigate! %(url)s
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


def _process_mail(mail_string, mail_type=None, manual=False):
    parser = EmailParser()
    if mail_type is None:
        email = parser.parse(BytesIO(mail_string))
    elif mail_type == 'postmark':
        email = parser.parse_postmark(json.loads(mail_string.decode('utf-8')))
    return _deliver_mail(email, mail_string=mail_string, manual=manual)


def create_deferred(secret_mail, mail_string, b64_encoded=False, spam=False,
                    subject=_('Unknown FoI-Mail Recipient'), body=unknown_foimail_message):
    from .models import DeferredMessage

    if mail_string is not None:
        if not b64_encoded:
            mail_string = base64.b64encode(mail_string.encode('utf-8')).decode("utf-8")
    DeferredMessage.objects.create(
        recipient=secret_mail,
        mail=mail_string,
        spam=spam
    )
    with override(settings.LANGUAGE_CODE):
        mail_managers(subject,
            body % {
                'address': secret_mail,
                'url': settings.SITE_URL + reverse('admin:foirequest_deferredmessage_changelist')
            }
        )


def get_alternative_mail(req):
    name = get_name_from_number(req.pk)
    domains = settings.FOI_EMAIL_DOMAIN
    if isinstance(domains, string_types):
        domains = [domains]
    if len(domains) > 1:
        domains = domains[1:]

    random.shuffle(domains)
    return '%s_%s@%s' % (name, req.pk, domains[0])


def get_foirequest_from_mail(email):
    from .models import FoiRequest

    if '_' in email:
        name, domain = email.split('@', 1)
        hero, num = name.rsplit('_', 1)
        try:
            num = int(num)
        except ValueError:
            return None
        hero_name = get_name_from_number(num)
        if hero_name != name:
            return None
        try:
            return FoiRequest.objects.get(pk=num)
        except FoiRequest.DoesNotExist:
            return None

    else:
        try:
            return FoiRequest.objects.get_by_secret_mail(email)
        except FoiRequest.DoesNotExist:
            return None


def _deliver_mail(email, mail_string=None, manual=False):
    from .models import DeferredMessage

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

        foi_request = get_foirequest_from_mail(secret_mail)
        if not foi_request:
            try:
                deferred = DeferredMessage.objects.get(recipient=secret_mail, request__isnull=False)
                foi_request = deferred.request
            except DeferredMessage.DoesNotExist:
                create_deferred(secret_mail, mail_string, b64_encoded=b64_encoded, spam=False)
                continue

        # Check for spam
        if not manual:
            messages = foi_request.response_messages()
            reply_domains = set(m.sender_email.split('@')[1] for m in messages
                             if m.sender_email and '@' in m.sender_email)
            reply_domains.add(foi_request.public_body.email.split('@')[1])
            strip_subdomains = lambda x: '.'.join(x.split('.')[-2:])
            # Strip subdomains
            reply_domains = set([strip_subdomains(x) for x in reply_domains])

            sender_email = email['from'][1]
            if len(messages) > 0 and sender_email and '@' in sender_email:
                email_domain = strip_subdomains(sender_email.split('@')[1])
                if email_domain not in reply_domains:
                    create_deferred(secret_mail, mail_string, b64_encoded=b64_encoded,
                        spam=True, subject=_('Possible Spam Mail received'), body=spam_message)
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
                if not attachment.file:
                    continue
                filename = '%s-%s' % (date_prefix, attachment.name)
                zfile.write(attachment.file.path, arcname=filename)
        zfile.close()
    return zfile_obj.getvalue()
