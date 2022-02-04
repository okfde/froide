import base64
import json
import random
import zipfile
from contextlib import closing, contextmanager
from email.utils import parseaddr
from io import BytesIO
from typing import Iterator, Optional, Tuple

from django.conf import settings
from django.core.mail import EmailMessage, get_connection, mail_managers
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from froide.helper.email_parsing import parse_email, parse_postmark
from froide.helper.email_utils import (
    get_mail_client,
    get_unread_mails,
    make_address,
    unflag_mail,
)
from froide.helper.name_generator import get_name_from_number, get_old_name_from_number

from .utils import get_foi_mail_domains, get_publicbody_for_email

unknown_foimail_subject = _("Unknown FoI-Mail Recipient")
unknown_foimail_message = _(
    """We received an FoI mail from <%(from_address)s> to this address: %(address)s.
No corresponding request could be identified, please investigate! %(url)s
"""
)

spam_message = _(
    """We received a possible spam mail to this address: %(address)s.
Please investigate! %(url)s
"""
)

DSN_RCPT_OPTIONS = ["NOTIFY=SUCCESS,DELAY,FAILURE"]


def send_foi_mail(
    subject,
    message,
    from_email,
    recipient_list,
    attachments=None,
    fail_silently=False,
    **kwargs
):
    backend_kwargs = {}
    if kwargs.get("dsn"):
        backend_kwargs["rcpt_options"] = DSN_RCPT_OPTIONS

    connection = get_connection(
        backend=settings.EMAIL_BACKEND,
        username=settings.FOI_EMAIL_HOST_USER,
        password=settings.FOI_EMAIL_HOST_PASSWORD,
        host=settings.FOI_EMAIL_HOST,
        port=settings.FOI_EMAIL_PORT,
        use_tls=settings.FOI_EMAIL_USE_TLS,
        fail_silently=fail_silently,
        **backend_kwargs
    )
    headers = {}
    if settings.FOI_EMAIL_FIXED_FROM_ADDRESS:
        name, mailaddr = parseaddr(from_email)
        from_address = settings.FOI_EMAIL_HOST_FROM
        from_email = make_address(from_address, name)
        headers["Reply-To"] = make_address(mailaddr, name)
    else:
        headers["Reply-To"] = from_email

    if kwargs.get("read_receipt"):
        headers["Disposition-Notification-To"] = from_email
    if kwargs.get("delivery_receipt"):
        headers["Return-Receipt-To"] = from_email
    if kwargs.get("froide_message_id"):
        headers["X-Froide-Message-Id"] = kwargs.get("froide_message_id")
    if kwargs.get("message_id"):
        headers["Message-Id"] = kwargs["message_id"]

    email = EmailMessage(
        subject,
        message,
        from_email,
        recipient_list,
        connection=connection,
        headers=headers,
    )
    if attachments is not None:
        for name, data, mime_type in attachments:
            email.attach(name, data, mime_type)
    return email.send()


def _process_mail(mail_bytes, mail_uid=None, mail_type=None, manual=False):
    email = None
    if mail_type is None:
        with closing(BytesIO(mail_bytes)) as stream:
            email = parse_email(stream)
    elif mail_type == "postmark":
        email = parse_postmark(json.loads(mail_bytes.decode("utf-8")))
    assert email is not None

    _deliver_mail(email, mail_bytes=mail_bytes, manual=manual)

    # Unflag mail after delivery is complete
    if mail_uid is not None:
        with get_foi_mail_client() as mailbox:
            unflag_mail(mailbox, mail_uid)


def create_deferred(
    secret_mail,
    mail_bytes,
    spam=False,
    sender_email=None,
    subject=unknown_foimail_subject,
    body=unknown_foimail_message,
    request=None,
):
    from .models import DeferredMessage

    mail_string = ""
    if mail_bytes is not None:
        mail_string = base64.b64encode(mail_bytes).decode("utf-8")
    DeferredMessage.objects.create(
        recipient=secret_mail,
        sender=sender_email or "",
        mail=mail_string,
        spam=spam,
        request=request,
    )
    if spam:
        # Do not notify on identified spam
        return

    with override(settings.LANGUAGE_CODE):
        url = reverse("admin:foirequest_deferredmessage_changelist")
        mail_managers(
            subject,
            body
            % {
                "address": secret_mail,
                "url": settings.SITE_URL + url,
                "from_address": sender_email,
            },
        )


def get_alternative_mail(req):
    name = get_name_from_number(req.pk)
    domains = get_foi_mail_domains()
    if len(domains) > 1:
        domains = domains[1:]

    random.shuffle(domains)
    return "%s_%s@%s" % (name, req.pk, domains[0])


def get_foirequest_from_mail(email):
    from .models import FoiRequest

    if "_" in email:
        name, domain = email.split("@", 1)
        hero, num = name.rsplit("_", 1)
        try:
            num = int(num)
        except ValueError:
            return None
        hero_name = get_name_from_number(num)
        old_hero_name = get_old_name_from_number(num)
        if hero_name != hero and old_hero_name != hero:
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


def _deliver_mail(email, mail_bytes=None, manual=False):
    received_list = email.to + email.cc + email.resent_to + email.resent_cc
    received_list = [(r[0], r[1].lower()) for r in received_list]

    domains = get_foi_mail_domains()

    def mail_filter(x):
        return x[1].endswith(tuple(["@%s" % d for d in domains]))

    received_list = [r for r in received_list if mail_filter(r)]

    # normalize to first FOI_EMAIL_DOMAIN
    received_list = [
        (x[0], "@".join((x[1].split("@")[0], domains[0]))) for x in received_list
    ]

    sender_email = email.from_[1]

    already = set()
    for received in received_list:
        recipient_email = received[1]
        if recipient_email in already:
            continue
        already.add(recipient_email)
        foirequest, pb = check_delivery_conditions(
            recipient_email,
            sender_email,
            parsed_email=email,
            mail_bytes=mail_bytes,
            manual=manual,
        )
        if foirequest is not None:
            add_message_from_email(foirequest, email, publicbody=pb)


def add_message_from_email(foirequest, email, publicbody=None):
    from .services import ReceiveEmailService

    service = ReceiveEmailService(email, foirequest=foirequest, publicbody=publicbody)
    service.process()


def check_delivery_conditions(
    recipient_mail, sender_email, parsed_email=None, mail_bytes=b"", manual=False
):
    from .models import DeferredMessage, FoiRequest

    if (
        not settings.FOI_EMAIL_FIXED_FROM_ADDRESS
        and recipient_mail == settings.FOI_EMAIL_HOST_USER
    ):
        # foi mailbox email, but custom email required, dropping
        return None, None

    previous_spam_sender = DeferredMessage.objects.filter(
        sender=sender_email, spam=True
    ).exists()
    if previous_spam_sender:
        # Drop previous spammer
        return None, None

    foirequest = get_foirequest_from_mail(recipient_mail)
    if not foirequest:
        # Find previous non-spam matching
        request_ids = DeferredMessage.objects.filter(
            recipient=recipient_mail, request__isnull=False, spam=False
        ).values_list("request_id", flat=True)
        if len(set(request_ids)) != 1:
            # Can't do automatic matching!
            create_deferred(
                recipient_mail, mail_bytes, sender_email=sender_email, spam=None
            )
            return None, None
        else:
            foirequest = FoiRequest.objects.get(id=list(request_ids)[0])

    pb = None
    if manual:
        return foirequest, pb

    if foirequest.closed:
        # Request is closed and will not receive messages
        return None, None

    # Check for spam
    pb = get_publicbody_for_email(sender_email, foirequest, include_deferred=True)
    if pb:
        return foirequest, pb

    if parsed_email.bounce_info.is_bounce:
        return foirequest, None

    is_spammer = None
    if sender_email is not None:
        is_spammer = DeferredMessage.objects.filter(
            sender=sender_email, spam=True
        ).exists()
        # If no spam found, treat as unknown
        is_spammer = is_spammer or None

    create_deferred(
        recipient_mail,
        mail_bytes,
        spam=is_spammer,
        sender_email=sender_email,
        subject=_("Possible Spam Mail received"),
        body=spam_message,
        request=foirequest,
    )
    return None, None


@contextmanager
def get_foi_mail_client():
    with get_mail_client(
        settings.FOI_EMAIL_HOST_IMAP,
        settings.FOI_EMAIL_PORT_IMAP,
        settings.FOI_EMAIL_ACCOUNT_NAME,
        settings.FOI_EMAIL_ACCOUNT_PASSWORD,
        ssl=settings.FOI_EMAIL_USE_SSL,
    ) as mailbox:
        yield mailbox


def _fetch_mail(flag_in_process=True) -> Iterator[Tuple[Optional[str], bytes]]:
    with get_foi_mail_client() as mailbox:
        yield from get_unread_mails(mailbox, flag=flag_in_process)


def fetch_and_process():
    count = 0
    for _mail_uid, rfc_data in _fetch_mail(flag_in_process=False):
        _process_mail(rfc_data, mail_uid=None)
        count += 1
    return count


def generate_foirequest_files(foirequest):
    from .pdf_generator import FoiRequestPDFGenerator

    pdf_generator = FoiRequestPDFGenerator(foirequest)
    correspondence_bytes = pdf_generator.get_pdf_bytes()
    yield ("%s.pdf" % foirequest.pk, correspondence_bytes, "application/pdf")
    yield from get_attachments_for_package(foirequest)


def get_attachments_for_package(foirequest):
    last_date = None
    date_count = 1

    for message in foirequest.messages:
        current_date = message.timestamp.date()
        date_prefix = current_date.isoformat()
        if current_date == last_date:
            date_count += 1
        else:
            date_count = 1
        date_prefix += "_%d" % date_count
        last_date = current_date

        att_queryset = message.foiattachment_set.filter(
            is_redacted=False, is_converted=False
        )

        for attachment in att_queryset:
            if not attachment.file:
                continue
            filename = "%s-%s" % (date_prefix, attachment.name)
            with open(attachment.file.path, "rb") as f:
                yield (filename, f.read(), attachment.filetype)


def package_foirequest(foirequest):
    from .pdf_generator import FoiRequestPDFGenerator

    zfile_obj = BytesIO()
    with override(settings.LANGUAGE_CODE):
        zfile = zipfile.ZipFile(zfile_obj, "w")
        path = str(foirequest.pk)
        pdf_generator = FoiRequestPDFGenerator(foirequest)
        correspondence_bytes = pdf_generator.get_pdf_bytes()
        zfile.writestr("%s/%s.pdf" % (path, foirequest.pk), correspondence_bytes)
        atts = get_attachments_for_package(foirequest)
        for filename, filebytes, _ct in atts:
            zfile.writestr("%s/%s" % (path, filename), filebytes)
        zfile.close()
    return zfile_obj.getvalue()
