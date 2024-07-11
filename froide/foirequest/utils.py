import json
import re
import zipfile
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from pathlib import PurePath
from typing import Iterator, List, Optional, Tuple, Union

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.mail import mail_managers
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

import icalendar

from froide.helper.content_urls import get_content_url
from froide.helper.date_utils import format_seconds
from froide.helper.email_utils import delete_mails_by_recipient
from froide.helper.storage import make_unique_filename
from froide.helper.tasks import search_instance_save
from froide.helper.text_utils import (
    apply_text_replacements,
    find_all_emails,
    redact_plaintext,
    redact_subject,
    redact_user_strings,
)
from froide.proof.models import ProofAttachment
from froide.publicbody.models import FoiLaw, PublicBody

from .models import FoiAttachment, FoiRequest

MAX_ATTACHMENT_SIZE = settings.FROIDE_CONFIG["max_attachment_size"]
RECIPIENT_BLOCKLIST = settings.FROIDE_CONFIG.get("recipient_blocklist_regex", None)


@dataclass
class PublicBodyEmailInfo:
    email: str
    name: str
    publicbody: Optional[PublicBody] = None
    label: Optional[str] = None

    def get_label(self):
        return self.label if self.label is not None else self.name


def throttle(qs, throttle_config, date_param="created_at"):
    if throttle_config is None:
        return False

    # Return True if the next request would break any limit
    for count, seconds in throttle_config:
        f = {"%s__gte" % date_param: timezone.now() - timedelta(seconds=seconds)}
        if qs.filter(**f).count() + 1 > count:
            return (count, seconds)
    return False


def check_throttle(user, klass, extra_filters=None):
    if not user.is_authenticated or user.trusted():
        return

    queryset = klass._default_manager.all()
    throttle_config = klass.get_throttle_config()
    queryset, date_param = klass.objects.get_throttle_filter(
        queryset, user, extra_filters=extra_filters
    )
    throttle_kind = throttle(queryset, throttle_config, date_param=date_param)
    if not throttle_kind:
        return

    if settings.FROIDE_CONFIG.get("request_throttle_mail"):
        mail_managers(_("User exceeded request limit"), str(user.pk))
    return forms.ValidationError(
        klass.get_throttle_message(),
        params={
            "count": throttle_kind[0],
            "time": format_seconds(throttle_kind[1]),
            "url": get_content_url("throttled"),
        },
        code="throttled",
    )


def get_foi_mail_domains() -> Union[List[str], Tuple[str]]:
    domains = settings.FOI_EMAIL_DOMAIN
    if not isinstance(domains, (list, tuple)):
        return [domains]
    return domains


def generate_secret_address(user, length=10):
    allowed_chars = "abcdefghkmnprstuvwxyz2345689"
    username = user.username.replace("_", ".")
    secret = get_random_string(length=length, allowed_chars=allowed_chars)
    template = getattr(settings, "FOI_EMAIL_TEMPLATE", None)

    FOI_EMAIL_DOMAIN = get_foi_mail_domains()[0]

    if template is not None and callable(template):
        return settings.FOI_EMAIL_TEMPLATE(username=username, secret=secret)
    elif template is not None:
        return settings.FOI_EMAIL_TEMPLATE.format(
            username=username, secret=secret, domain=FOI_EMAIL_DOMAIN
        )
    return "%s.%s@%s" % (username, secret, FOI_EMAIL_DOMAIN)


def build_secret_url_regexes(url_name):
    obj_id = "0"
    code = "deadbeef"
    url = reverse(url_name, kwargs={"obj_id": obj_id, "code": code})
    url = url.replace(obj_id, r"(\d+)")
    url = url.replace(code, r"[0-9a-f]+")
    # cut of trailing slash to extend match
    url = url[:-1]
    return re.compile(url)


SECRET_URL_NAMES = [
    "foirequest-auth",
    "foirequest-longerauth",
    "foirequest-publicbody_upload",
]
SECRET_URL_REPLACEMENTS = {}


def get_secret_url_replacements():
    if SECRET_URL_REPLACEMENTS:
        return SECRET_URL_REPLACEMENTS

    url_regexes = [build_secret_url_regexes(url_name) for url_name in SECRET_URL_NAMES]
    replacement_url = reverse("foirequest-shortlink", kwargs={"obj_id": "0"})
    replacement_url = replacement_url.replace("0", r"\1")

    replacements = {key: replacement_url for key in url_regexes}
    SECRET_URL_REPLACEMENTS.update(replacements)
    return SECRET_URL_REPLACEMENTS


def short_request_url(name, foirequest, message=None):
    params = {"slug": foirequest.slug}
    if message:
        params["message_id"] = message.id
    url_path = reverse(name, kwargs=params)
    fr_path = foirequest.get_absolute_url()
    url_path = re.sub("^{}".format(fr_path), "/", url_path)

    return reverse(
        "foirequest-shortlink_url",
        kwargs={"obj_id": foirequest.pk, "url_path": url_path},
    )


def get_minimum_redaction_replacements(foirequest: FoiRequest):
    replacements = dict(get_secret_url_replacements())
    pattern = re.compile(re.escape(foirequest.secret_address))
    replacements[pattern] = str(_("<<email address>>"))
    return replacements


def apply_minimum_redaction(foirequest: FoiRequest, plaintext: str) -> str:
    replacements = get_minimum_redaction_replacements(foirequest)
    plaintext = apply_text_replacements(plaintext, replacements)
    return plaintext


def redact_plaintext_with_request(
    plaintext, foirequest, redact_greeting=False, redact_closing=False
):
    replacements = get_secret_url_replacements()
    user_replacements = foirequest.user.get_redactions()
    return redact_plaintext(
        plaintext,
        redact_greeting=redact_greeting,
        redact_closing=redact_closing,
        user_replacements=user_replacements,
        replacements=replacements,
    )


def construct_initial_message_body(
    foirequest: FoiRequest,
    text: str = "",
    foilaw: Optional[FoiLaw] = None,
    full_text: bool = False,
    send_address: bool = True,
    attachment_names: Optional[List[str]] = None,
    attachment_missing: Optional[List[str]] = None,
    proof: Optional[ProofAttachment] = None,
    template="foirequest/emails/mail_with_userinfo.txt",
):
    if full_text:
        body = "{body}\n{name}".format(body=text, name=foirequest.user.get_full_name())
    else:
        letter_start, letter_end = "", ""
        if foilaw:
            letter_start = foilaw.letter_start
            letter_end = foilaw.letter_end
        body = ("{letter_start}\n\n{body}\n\n{letter_end}\n\n{name}").format(
            letter_start=letter_start,
            body=text,
            letter_end=letter_end,
            name=foirequest.user.get_full_name(),
        )
    return construct_message_body(
        foirequest,
        text=body,
        send_address=send_address,
        attachment_names=attachment_names,
        attachment_missing=attachment_missing,
        proof=proof,
        template=template,
    )


def construct_message_body(
    foirequest: FoiRequest,
    text: str,
    send_address: bool = True,
    attachment_names: Optional[List[str]] = None,
    attachment_missing: Optional[List[str]] = None,
    template: str = "foirequest/emails/mail_with_userinfo.txt",
    proof: Optional[ProofAttachment] = None,
):
    return render_to_string(
        template,
        {
            "request": foirequest,
            "body": text,
            "attachment_names": attachment_names,
            "attachment_missing": attachment_missing,
            "send_address": send_address,
            "proof": proof,
        },
    )


def strip_subdomains(domain):
    return ".".join(domain.split(".")[-2:])


def get_host(email):
    if email and "@" in email:
        return email.rsplit("@", 1)[1].lower()
    return None


def get_domain(email):
    host = get_host(email)
    if host is None:
        return None
    return strip_subdomains(host)


def compare_publicbody_email_with_transform(
    email: str, pb_info_list: List[PublicBodyEmailInfo], transform=str.lower
):
    email = transform(email)

    for pb_info in pb_info_list:
        if pb_info.publicbody and transform(pb_info.email) == email:
            return pb_info.publicbody


def compare_publicbody_email(
    email: str, pb_info_list: List[PublicBodyEmailInfo], compare_tld=True
) -> Optional[PublicBody]:
    # Compare email direct
    pb = compare_publicbody_email_with_transform(email, pb_info_list)
    if pb:
        return pb

    # Compare email full host
    pb = compare_publicbody_email_with_transform(
        email, pb_info_list, transform=get_host
    )
    if pb:
        return pb

    if not compare_tld:
        return None

    # Compare email domain without subdomains
    return compare_publicbody_email_with_transform(
        email, pb_info_list, transform=get_domain
    )


def get_publicbody_for_email(
    email: str, foirequest: FoiRequest, include_deferred: bool = False
) -> Optional[PublicBody]:
    if not email:
        return None

    pb_info_list = list(get_emails_from_request(foirequest))

    pb = compare_publicbody_email(email, pb_info_list)
    if pb:
        return pb

    # Search in all PublicBodies
    email_host = get_host(email)
    if email_host is None:
        return None
    pbs = PublicBody.objects.filter(email__endswith=email_host)
    if len(pbs) == 1:
        return pbs[0]
    elif foirequest.public_body in pbs:
        # likely the request's public body
        return foirequest.public_body

    if include_deferred:
        from .models import DeferredMessage

        pb = DeferredMessage.objects.get_publicbody_for_email(email)
        if pb is not None:
            return pb

    return None


def send_request_user_email(
    mail_intent,
    foirequest,
    subject=None,
    context=None,
    add_idmark=True,
    priority=True,
    start_thread=False,
    **kwargs
):
    if not foirequest.user:
        return
    if subject and add_idmark:
        subject = "{} [#{}]".format(subject, foirequest.pk)

    context.update({"user": foirequest.user})
    headers = {}
    domain = settings.SITE_URL.split("/")[-1]
    thread_id = "<foirequest/{id}@{domain}>".format(id=foirequest.id, domain=domain)
    if start_thread:
        headers["Message-ID"] = thread_id
    else:
        headers["References"] = thread_id
        headers["In-Reply-To"] = thread_id

    headers["List-ID"] = "foirequest/{id} <{id}.foirequest.{domain}>".format(
        id=foirequest.id, domain=domain
    )
    headers["List-Archive"] = foirequest.get_absolute_domain_short_url()

    mail_intent.send(
        user=foirequest.user,
        subject=subject,
        context=context,
        priority=priority,
        headers=headers,
        **kwargs
    )


def get_info_for_email(foirequest, email):
    email = email.lower()
    for email_info in get_emails_from_request(foirequest):
        if email == email_info.email.lower():
            return email_info
    return PublicBodyEmailInfo(email="", name="")


def get_publicbody_emails(publicbody: PublicBody, include_mediator=True):
    if publicbody.email:
        email = publicbody.email
        yield PublicBodyEmailInfo(
            email=email,
            name=publicbody.name,
            label=_("Default address of {publicbody}").format(
                publicbody=publicbody.name
            ),
            publicbody=publicbody,
        )
    if publicbody.alternative_emails:
        for law_type, email in publicbody.alternative_emails.items():
            yield PublicBodyEmailInfo(
                email=email,
                name=publicbody.name,
                label=_("Default {law_type} address of {publicbody}").format(
                    law_type=law_type, publicbody=publicbody.name
                ),
                publicbody=publicbody,
            )

    if include_mediator:
        mediator = publicbody.get_mediator()
        if mediator:
            yield PublicBodyEmailInfo(
                email=mediator.email,
                name=mediator.name,
                label=_("{publicbody} (mediator)").format(publicbody=mediator.name),
                publicbody=mediator,
            )


def get_emails_from_request_iterator(
    foirequest, include_mediator=True
) -> Iterator[PublicBodyEmailInfo]:
    if foirequest.public_body:
        # Get emails from public body / mediator
        yield from get_publicbody_emails(
            foirequest.public_body, include_mediator=include_mediator
        )

    # Get emails from response messages,
    domains = tuple(get_foi_mail_domains())
    messages = foirequest.response_messages()
    for message in reversed(messages):
        email = message.sender_email
        if not email and message.sender_public_body:
            email = message.sender_public_body.email

        if email:
            yield PublicBodyEmailInfo(
                email=email,
                name=message.sender_name,
                publicbody=message.sender_public_body,
            )

    # Get emails from response messages other recipients
    for message in reversed(messages):
        if message.email_headers:
            for email in get_emails_from_message_headers(message.email_headers):
                if email.endswith(domains):
                    continue
                yield PublicBodyEmailInfo(
                    email=email,
                    name="",
                    publicbody=None,
                )

    for message in reversed(messages):
        for email in find_all_emails(message.plaintext):
            if email.endswith(domains):
                continue
            yield PublicBodyEmailInfo(email=email, name=email, publicbody=None)

    if foirequest.public_body.parent and foirequest.public_body.parent.email:
        email = foirequest.public_body.parent.email.lower()
        yield PublicBodyEmailInfo(
            email=email,
            name=foirequest.public_body.parent.name,
            publicbody=foirequest.public_body.parent,
        )


def get_emails_from_request(
    foirequest: FoiRequest, include_mediator: bool = True
) -> Iterator[PublicBodyEmailInfo]:
    already = set()
    pb_info_list = list(
        get_emails_from_request_iterator(foirequest, include_mediator=include_mediator)
    )

    for pb_info in pb_info_list:
        email = pb_info.email.lower()
        if email in already:
            continue
        if not pb_info.publicbody:
            pb = compare_publicbody_email(email, pb_info_list, compare_tld=False)
            if pb:
                pb_info.publicbody = pb
        yield pb_info
        already.add(email)


def get_emails_from_message_headers(email_headers):
    fields = ("to", "cc", "resent-to", "resent-cc")
    for field in fields:
        for addr in email_headers.get(field, []):
            email = addr[1]
            if not email:
                continue
            try:
                validate_email(email)
                yield email
            except ValidationError:
                pass


def possible_reply_addresses(foirequest):
    FOI_MAIL_DOMAIN = get_foi_mail_domains()[0]
    options = []
    for email_info in get_emails_from_request(foirequest, include_mediator=False):
        # Don't reply to our own addesses
        if email_info.email.endswith("@{}".format(FOI_MAIL_DOMAIN)):
            continue
        if RECIPIENT_BLOCKLIST and RECIPIENT_BLOCKLIST.match(email_info.email):
            continue
        if "@" not in email_info.email:
            continue
        label = email_info.get_label()
        if email_info.email not in label:
            if not label:
                label = email_info.email
            else:
                label = "{} ({})".format(label, email_info.email)
        options.append((email_info.email, label))
    return options


class MailAttachmentSizeChecker:
    def __init__(self, generator, max_size=MAX_ATTACHMENT_SIZE):
        self.generator = generator
        self.max_size = max_size

    def __iter__(self):
        sum_bytes = 0
        self.non_send_files = []
        self.send_files = []
        for name, filebytes, mimetype in self.generator:
            sum_bytes += len(filebytes)
            if sum_bytes > self.max_size:
                self.non_send_files.append(name)
            else:
                self.send_files.append(name)
                yield name, filebytes, mimetype


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership

    from .models import (
        FoiEvent,
        FoiMessage,
        FoiProject,
        FoiRequest,
        PublicBodySuggestion,
        RequestDraft,
    )

    mapping = [
        (FoiRequest, "user", None),
        (PublicBodySuggestion, "user", None),
        (FoiMessage, "sender_user", None),
        (FoiEvent, "user", None),
        (FoiProject, "user", None),
        (RequestDraft, "user", None),
    ]
    for model, attr, dupe in mapping:
        move_ownership(model, attr, old_user, new_user, dupe=dupe)
    update_foirequest_index(FoiRequest.objects.filter(user=new_user))


def cancel_user(sender, user=None, **kwargs):
    from .models import FoiRequest, RequestDraft

    if user is None:
        return

    user_foirequests = FoiRequest.objects.filter(user=user)
    delete_foirequest_emails_from_imap(user_foirequests)

    FoiRequest.objects.delete_private_requests(user)
    RequestDraft.objects.filter(user=user).delete()

    permanently_anonymize_requests(user_foirequests.select_related("user"))


def delete_foirequest_emails_from_imap(user_foirequests) -> int:
    from .foi_mail import get_foi_mail_client

    with get_foi_mail_client() as mailbox:
        message_count = 0
        for foirequest in user_foirequests:
            parts = foirequest.secret_address.split("@")
            # Sanity check recipient address
            assert len(parts) == 2
            assert len(parts[0]) > 5
            assert parts[1] in get_foi_mail_domains()
            message_count += delete_mails_by_recipient(
                mailbox, foirequest.secret_address, expunge=True
            )
    return message_count


def make_account_private(sender, user=None, **kwargs):
    foirequests = user.foirequest_set.all()
    rerun_message_redaction(foirequests)


def rerun_message_redaction(foirequests):
    for foirequest in foirequests:
        user = foirequest.user
        user_replacements = user.get_redactions()
        for message in foirequest.messages:
            message.subject_redacted = redact_subject(
                message.subject, user_replacements
            )
            message.plaintext_redacted = redact_plaintext(
                message.plaintext,
                redact_closing=message.is_response,
                redact_greeting=not message.is_response,
                user_replacements=user_replacements,
            )
            message.clear_render_cache()
            message.save()


def permanently_anonymize_requests(foirequests):
    from .models import FoiAttachment

    # Old secret address contained plus, new dot, split by either
    SECRET_ADDRESS_SPLITTER = re.compile(r"[\.\+]")

    replacements = {
        "name": str(_("<information-removed>")),
        "email": str(_("<information-removed>")),
        "address": str(_("<information-removed>")),
    }
    original_private = True
    if foirequests:
        original_private = foirequests[0].user.private
    for foirequest in foirequests:
        foirequest.closed = True
        # Cut off name part of secret address
        foirequest.secret_address = "~" + ".".join(
            SECRET_ADDRESS_SPLITTER.split(foirequest.secret_address)[2:]
        )
        foirequest.save()
        user = foirequest.user
        user_replacements = user.get_redactions(replacements)
        user.private = True
        for message in foirequest.messages:
            if message.plaintext_redacted:
                message.plaintext_redacted = redact_user_strings(
                    message.plaintext_redacted,
                    user_replacements=user_replacements,
                )
            message.plaintext = redact_user_strings(
                message.plaintext,
                user_replacements=user_replacements,
            )
            message.clear_render_cache()
            message.html = ""
            if message.is_response:
                # This may occasionally delete real sender name
                # when user was only in CC
                message.recipient = ""
                message.recipient_email = ""
            else:
                message.sender_name = ""

            message.save()

        # Delete original attachments, if they have a redacted version
        atts = FoiAttachment.objects.filter(
            approved=False,
            can_approve=False,
            belongs_to__request=foirequest,
            redacted__isnull=False,
            is_redacted=False,
        )
        for att in atts:
            att.remove_file_and_delete()

        if not original_private:
            # Set other attachments to non-approved, if user was not private
            FoiAttachment.objects.filter(belongs_to__request=foirequest).update(
                approved=False
            )
    update_foirequest_index(foirequests)


def add_ical_events(foirequest, cal):
    event_timezone = timezone.get_current_timezone()

    def tz(x):
        return x.astimezone(event_timezone)

    uid = "event-%s-{pk}@{domain}".format(
        pk=foirequest.id, domain=settings.SITE_URL.split("/")[-1]
    )

    title = "{} [#{}]".format(foirequest.title, foirequest.pk)
    url = settings.SITE_URL + foirequest.get_absolute_url()

    event = icalendar.Event()
    event.add("uid", uid % "request")
    event.add("dtstamp", tz(timezone.now()))
    event.add("dtstart", tz(foirequest.first_message))
    event.add("url", url)
    event.add("summary", title)
    event.add("description", foirequest.description)
    cal.add_component(event)

    if foirequest.due_date:
        event = icalendar.Event()
        event.add("uid", uid % "duedate")
        event.add("dtstamp", tz(timezone.now()))
        event.add("dtstart", tz(foirequest.due_date).date())
        event.add("url", url)
        event.add("summary", _("Due date: %s") % title)
        event.add("description", foirequest.description)
        cal.add_component(event)

    if foirequest.status == "awaiting_response" and (
        foirequest.resolution
        in (foirequest.RESOLUTION.PARTIALLY_SUCCESSFUL, foirequest.RESOLUTION.REFUSED)
    ):
        responses = foirequest.response_messages()
        if responses:
            appeal_deadline = foirequest.law.calculate_due_date(
                date=responses[-1].timestamp
            )
            event = icalendar.Event()
            event.add("uid", uid % "appeal_deadline")
            event.add("dtstamp", tz(timezone.now()))
            event.add("dtstart", tz(appeal_deadline).date())
            event.add("url", url)
            event.add("summary", _("Appeal deadline: %s") % title)
            event.add("description", foirequest.description)
            alarm = icalendar.Alarm()
            alarm.add("trigger", icalendar.prop.vDuration(-timedelta(days=1)))
            alarm.add("action", "DISPLAY")
            alarm.add("description", _("Appeal deadline: %s") % title)
            event.add_component(alarm)
            cal.add_component(event)


def export_user_data(user):
    from froide.helper.api_utils import get_fake_api_context

    from .api_views import (
        FoiAttachmentSerializer,
        FoiMessageSerializer,
        FoiRequestListSerializer,
    )
    from .models import FoiAttachment, FoiProject

    ctx = get_fake_api_context()
    foirequests = user.foirequest_set.all().iterator()

    for foirequest in foirequests:
        data = FoiRequestListSerializer(foirequest, context=ctx).data
        data["secret_address"] = foirequest.secret_address
        yield (
            "requests/%s/request.json" % foirequest.id,
            json.dumps(data).encode("utf-8"),
        )

        messages = foirequest.get_messages(with_tags=True)
        for message in messages:
            data = FoiMessageSerializer(message, context=ctx).data
            yield (
                "requests/%s/%s/message.json" % (foirequest.id, message.id),
                json.dumps(data).encode("utf-8"),
            )

        all_attachments = FoiAttachment.objects.select_related("redacted").filter(
            belongs_to__request=foirequest
        )
        if all_attachments:
            yield (
                "requests/%s/%s/attachments.json" % (foirequest.id, message.id),
                json.dumps(
                    [
                        FoiAttachmentSerializer(att, context=ctx).data
                        for att in all_attachments
                    ]
                ).encode("utf-8"),
            )
        for attachment in all_attachments:
            try:
                yield (
                    "requests/%s/%s/%s" % (foirequest.id, message.id, attachment.name),
                    attachment.get_bytes(),
                )
            except IOError:
                pass

    drafts = user.requestdraft_set.all()
    if drafts:
        yield (
            "drafts.json",
            json.dumps(
                [
                    {
                        "create_date": d.create_date.isoformat(),
                        "save_date": d.save_date.isoformat(),
                        "publicbodies": [p.id for p in d.publicbodies.all()],
                        "subject": d.subject,
                        "body": d.body,
                        "full_text": d.full_text,
                        "public": d.public,
                        "reference": d.reference,
                        "law_type": d.law_type,
                        "flags": d.flags,
                        "request": d.request_id,
                        "project": d.project_id,
                    }
                    for d in drafts
                ]
            ).encode("utf-8"),
        )
    suggestions = user.publicbodysuggestion_set.all()
    if suggestions:
        yield (
            "publicbody_suggestions.json",
            json.dumps(
                [
                    {
                        "timestamp": s.timestamp.isoformat(),
                        "publicbody": s.public_body_id,
                        "request": s.request_id,
                        "reasons": s.reason,
                    }
                    for s in suggestions
                ]
            ).encode("utf-8"),
        )

    events = user.foievent_set.all()
    if events:
        yield (
            "events.json",
            json.dumps(
                [
                    {
                        "timestamp": (e.timestamp.isoformat() if e.timestamp else None),
                        "publicbody": e.public_body_id,
                        "request": e.request_id,
                        "event_name": e.event_name,
                        "public": e.public,
                        "context": e.context,
                    }
                    for e in events
                ]
            ).encode("utf-8"),
        )

    projects = FoiProject.objects.get_for_user(user)
    if projects:
        yield (
            "projects.json",
            json.dumps(
                [
                    {
                        "title": p.title,
                        "slug": p.slug,
                        "description": p.description,
                        "status": p.status,
                        "created": p.created.isoformat() if p.created else None,
                        "last_update": p.last_update.isoformat()
                        if p.last_update
                        else None,
                        "public": p.public,
                        "team_id": p.team_id,
                        "request_count": p.request_count,
                        "request_ids": [x.id for x in p.foirequest_set.all()],
                        "reference": p.reference,
                        "publicbodies": [x.id for x in p.publicbodies.all()],
                        "site_id": p.site_id,
                    }
                    for p in projects
                ]
            ).encode("utf-8"),
        )


def update_foirequest_index(queryset):
    for foirequest_id in queryset.values_list("id", flat=True):
        search_instance_save.delay("foirequest.foirequest", foirequest_id)


def select_foirequest_template(foirequest, base_template: str):
    path, name = base_template.rsplit("/", 1)
    templates = []
    if foirequest.law and foirequest.law.law_type:
        templates.append("/".join((path, foirequest.law.law_type.lower(), name)))

    templates.append(base_template)
    return templates


ZIP_BLOCK_LIST = set(["__MACOSX", ".DS_Store"])
PATH_REPLACEMENT = "___"  # 3 underscores


def unpack_zipfile_attachment(attachment: FoiAttachment):
    import magic
    from filingcabinet.services import remove_common_root_path

    file_obj = attachment.file

    if not zipfile.is_zipfile(file_obj):
        return

    with zipfile.ZipFile(file_obj, "r") as zf:
        zip_paths = []
        for zip_info in zf.infolist():
            if zip_info.is_dir():
                continue
            path = PurePath(zip_info.filename)
            parts = path.parts
            if parts[0] in ZIP_BLOCK_LIST:
                continue
            zip_paths.append(path)
        if not zip_paths:
            return

        doc_paths = remove_common_root_path(zip_paths)
        names = set(
            attachment.belongs_to.foiattachment_set.all().values_list("name", flat=True)
        )
        for doc_path, zip_path in zip(doc_paths, zip_paths):
            attachment_name = PATH_REPLACEMENT.join(doc_path.parts)
            attachment_name = make_unique_filename(attachment_name, names)
            names.add(attachment_name)

            file_obj = BytesIO(zf.read(str(zip_path)))
            content_type = magic.from_buffer(file_obj.read(1024), mime=True)
            file_obj.seek(0)

            new_attachment = FoiAttachment(
                belongs_to=attachment.belongs_to,
                name=attachment_name,
                size=file_obj.getbuffer().nbytes,
                filetype=content_type,
                can_approve=not attachment.belongs_to.request.not_publishable,
            )
            new_attachment.file.save(attachment_name, File(file_obj))
