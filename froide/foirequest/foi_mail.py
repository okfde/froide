import base64
import random
import zipfile
from contextlib import closing, contextmanager
from io import BytesIO
from typing import Iterator, Optional, Tuple

from django.conf import settings
from django.core.mail import EmailMessage, get_connection, mail_managers
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from froide.foirequest.models import DeferredMessage, FoiMessage, FoiRequest
from froide.helper.email_parsing import ParsedEmail, parse_email, parse_email_address
from froide.helper.email_utils import (
    get_mail_client,
    get_unread_mails,
    make_address,
    unflag_mail,
)
from froide.helper.name_generator import get_name_from_number
from froide.publicbody.models import PublicBody

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
    bcc=None,
    attachments=None,
    fail_silently=False,
    **kwargs,
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
        **backend_kwargs,
    )
    headers = {}
    if settings.FOI_EMAIL_FIXED_FROM_ADDRESS:
        name, mailaddr = parse_email_address(from_email)
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
        bcc=bcc,
        connection=connection,
        headers=headers,
    )
    if attachments is not None:
        for name, data, mime_type in attachments:
            email.attach(name, data, mime_type)
    return email.send()


def _process_mail(mail_bytes, mail_uid=None, manual=False):
    email = None

    with closing(BytesIO(mail_bytes)) as stream:
        email = parse_email(stream)
    assert email is not None

    _deliver_mail(email, mail_bytes=mail_bytes, manual=manual)

    # Unflag mail after delivery is complete
    if mail_uid is not None:
        with get_foi_mail_client() as mailbox:
            unflag_mail(mailbox, mail_uid)


def create_deferred(
    secret_mail: str,
    mail_bytes: bytes,
    spam: Optional[bool] = None,
    sender_email: Optional[str] = None,
    subject=unknown_foimail_subject,
    body=unknown_foimail_message,
    foirequest: Optional[FoiRequest] = None,
):
    mail_string = ""
    if mail_bytes is not None:
        mail_string = base64.b64encode(mail_bytes).decode("utf-8")
    DeferredMessage.objects.create(
        recipient=secret_mail,
        sender=sender_email or "",
        mail=mail_string,
        spam=spam,
        request=foirequest,
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


def get_foirequest_from_mail(email: str) -> Optional[FoiRequest]:
    if "_" in email:
        name, domain = email.split("@", 1)
        hero, num = name.rsplit("_", 1)
        try:
            num = int(num)
        except ValueError:
            return None
        hero_name = get_name_from_number(num)
        if hero_name != hero:
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


class DeferredMessageNeeded(Exception):
    def __init__(self, *args, foirequest=None, **kwargs):
        self.foirequest = foirequest
        super().__init__(*args, **kwargs)


def _deliver_mail(email: ParsedEmail, mail_bytes=None, manual=False):
    received_list = (
        email.to + email.cc + email.resent_to + email.resent_cc + email.x_original_to
    )
    received_list = [r.lower() for r in received_list]

    domains = get_foi_mail_domains()

    def mail_filter(x):
        return x.email.endswith(tuple(["@%s" % d for d in domains]))

    received_list = [r for r in received_list if mail_filter(r)]

    # normalize to first FOI_EMAIL_DOMAIN
    received_list = [x.replace_email_domain(domains[0]) for x in received_list]

    sender_email = email.from_.email

    if not received_list:
        # Create a deferred message if the message is otherwise not handled
        create_deferred(
            "",
            mail_bytes,
            sender_email=sender_email,
        )

    already_emails = set()
    already_foirequests = set()
    for received in received_list:
        recipient_email = received.email
        if recipient_email in already_emails:
            continue
        already_emails.add(recipient_email)

        try:
            foirequest, publicbody = check_delivery_conditions(
                recipient_email, sender_email, parsed_email=email, manual=manual
            )
            if foirequest:
                if foirequest in already_foirequests:
                    # Only deliver once to an foirequest
                    continue
                already_foirequests.add(foirequest)
                add_message_from_email(foirequest, email, publicbody=publicbody)
        except DeferredMessageNeeded as deferred_exception:
            create_deferred(
                recipient_email,
                mail_bytes,
                sender_email=sender_email,
                foirequest=deferred_exception.foirequest,
            )


DeliveryConditionResult = Tuple[Optional[FoiRequest], Optional[PublicBody]]


def check_delivery_conditions(
    recipient_email: str,
    sender_email: str,
    parsed_email: ParsedEmail,
    manual: bool = False,
) -> DeliveryConditionResult:
    if should_drop_email(recipient_email, sender_email):
        return None, None

    foirequest = find_foirequest_for_delivery(recipient_email)
    if not foirequest:
        raise DeferredMessageNeeded

    publicbody = get_publicbody_for_email(
        sender_email, foirequest, include_deferred=True
    )

    if manual:
        # Force delivery to foirequest, no more checks
        return foirequest, publicbody

    if foirequest.closed:
        # Request is closed and will not receive messages
        return None, None

    if publicbody:
        # if email can be matched to public agency, deliver to foirequest
        return foirequest, publicbody

    if parsed_email.bounce_info.is_bounce:
        # If public agency cannot be found, but it's a bounce message, deliver
        return foirequest, None

    # No match and not bounce, raise DeferredMessageNeeded
    raise DeferredMessageNeeded(foirequest=foirequest)


def find_foirequest_for_delivery(recipient_email: str) -> Optional[FoiRequest]:
    foirequest = get_foirequest_from_mail(recipient_email)
    if foirequest:
        return foirequest

    # Find previous non-spam matching
    request_ids = DeferredMessage.objects.filter(
        recipient=recipient_email, request__isnull=False, spam=False
    ).values_list("request_id", flat=True)
    if len(set(request_ids)) != 1:
        raise DeferredMessageNeeded

    return FoiRequest.objects.get(id=list(request_ids)[0])


def add_message_from_email(
    foirequest: FoiRequest, email: ParsedEmail, publicbody: Optional[PublicBody] = None
):
    from .services import ReceiveEmailService

    service = ReceiveEmailService(email, foirequest=foirequest, publicbody=publicbody)
    service.process()


def should_drop_email(recipient_email: str, sender_email: str) -> bool:
    from .models import DeferredMessage

    if (
        not settings.FOI_EMAIL_FIXED_FROM_ADDRESS
        and recipient_email == settings.FOI_EMAIL_HOST_USER
    ):
        # foi mailbox email, but custom email required, dropping
        return True

    previous_spam_sender = DeferredMessage.objects.filter(
        sender=sender_email, spam=True
    ).exists()
    if previous_spam_sender:
        # Drop previous spammer
        return True

    return False


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
    yield ("_%s.pdf" % foirequest.pk, correspondence_bytes, "application/pdf")
    yield from get_message_attachments_for_package(foirequest)


def get_message_and_attachments(
    foimessage: FoiMessage, date_prefix: Optional[str] = None
):
    from .pdf_generator import FoiRequestMessagePDFGenerator

    if date_prefix is None:
        date_prefix = foimessage.timestamp.date().isoformat()

    pdf_generator = FoiRequestMessagePDFGenerator(foimessage)
    yield ("%s.pdf" % date_prefix, pdf_generator.get_pdf_bytes(), "application/pdf")

    att_queryset = foimessage.foiattachment_set.filter(
        is_redacted=False, is_converted=False
    )

    for attachment in att_queryset:
        if not attachment.file:
            continue
        filename = "%s-%s" % (date_prefix, attachment.name)
        with open(attachment.file.path, "rb") as f:
            yield (filename, f.read(), attachment.filetype)


def package_message(foimessage: FoiMessage):
    zfile_obj = BytesIO()
    with override(settings.LANGUAGE_CODE):
        zfile = zipfile.ZipFile(zfile_obj, "w")
        path = str(foimessage.request_id)
        atts = get_message_and_attachments(foimessage)
        for filename, filebytes, _ct in atts:
            zfile.writestr("%s/%s" % (path, filename), filebytes)
        zfile.close()
    return zfile_obj.getvalue()


def get_message_attachments_for_package(foirequest):
    last_date = None
    date_count = 1

    for foimessage in foirequest.messages:
        current_date = foimessage.timestamp.date()
        date_prefix = current_date.isoformat()
        if current_date == last_date:
            date_count += 1
        else:
            date_count = 1
        if date_count > 1:
            date_prefix += "_%d" % date_count

        last_date = current_date
        yield from get_message_and_attachments(foimessage, date_prefix=date_prefix)


def package_foirequest(foirequest: FoiRequest):
    from .pdf_generator import FoiRequestPDFGenerator

    zfile_obj = BytesIO()
    with override(settings.LANGUAGE_CODE):
        zfile = zipfile.ZipFile(zfile_obj, "w")
        path = str(foirequest.pk)
        pdf_generator = FoiRequestPDFGenerator(foirequest)
        correspondence_bytes = pdf_generator.get_pdf_bytes()
        zfile.writestr("%s/_%s.pdf" % (path, foirequest.pk), correspondence_bytes)
        atts = get_message_attachments_for_package(foirequest)
        for filename, filebytes, _ct in atts:
            zfile.writestr("%s/%s" % (path, filename), filebytes)
        zfile.close()
    return zfile_obj.getvalue()
