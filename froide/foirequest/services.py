import re
import uuid
from datetime import timedelta
from functools import partial

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.files import File
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from froide.account.services import AccountService
from froide.helper.db_utils import save_obj_with_slug
from froide.helper.email_parsing import ParsedEmail
from froide.helper.storage import make_unique_filename
from froide.helper.text_utils import redact_subject
from froide.problem.models import ProblemReport

from .hooks import registry
from .models import FoiAttachment, FoiMessage, FoiProject, FoiRequest, RequestDraft
from .models.message import (
    AUTO_REPLY_TAG,
    BOUNCE_RESENT_TAG,
    BOUNCE_TAG,
    HAS_BOUNCED_TAG,
)
from .tasks import convert_attachment_task, create_project_requests
from .utils import (
    construct_initial_message_body,
    generate_secret_address,
    get_publicbody_for_email,
    redact_plaintext_with_request,
)

User = get_user_model()


class BaseService(object):
    def __init__(self, data, **kwargs):
        self.data = data
        self.kwargs = kwargs

    def execute(self, request=None):
        return self.process(request=request)


def generate_unique_secret_address(user):
    while True:
        address = generate_secret_address(user)
        try:
            FoiRequest.objects.get(secret_address=address)
        except FoiRequest.DoesNotExist:
            break
    return address


class CreateRequestService(BaseService):
    def process(self, request=None):
        data = self.data
        user = data["user"]
        user_created = False
        user_auth = user.is_authenticated

        if not user_auth:
            user, user_created = AccountService.create_user(**self.data)
            self.data["user"] = user

        if not user_created and not user_auth:
            return self.create_token_draft(user)

        if request is not None:
            extra = registry.run_hook(
                "pre_request_creation", request, user=user, data=data
            )
            if extra is not None:
                data.update(extra)

        if len(self.data["publicbodies"]) > 1:
            foi_object = self.create_project()
        else:
            foi_object = self.create_request(self.data["publicbodies"][0])

            if user_created:
                AccountService(user).send_confirmation_mail(
                    reference=foi_object.reference,
                    redirect_url=self.data.get("redirect_url"),
                )
        self.post_creation(foi_object)
        return foi_object

    def create_token_draft(self, user):
        """
        User is not authenticated, but has given valid email.
        Create a draft object with a token, send token to email.

        """
        from .views import MakeRequestView

        data = self.data
        additional_kwargs = dict(
            subject=data.get("subject", ""),
            body=data.get("body", ""),
            full_text=data.get("full_text", False),
            public=data["public"],
            reference=data.get("reference", ""),
            law_type=data.get("law_type", ""),
        )

        flag_keys = set(MakeRequestView.FORM_CONFIG_PARAMS) | {"redirect_url"}
        flags = {k: v for k, v in data.items() if k in flag_keys}
        additional_kwargs["flags"] = flags

        draft = RequestDraft.objects.create(
            user=None, token=uuid.uuid4(), **additional_kwargs
        )
        draft.publicbodies.set(data["publicbodies"])

        claim_url = reverse("foirequest-claim_draft", kwargs={"token": draft.token})
        AccountService(user).send_confirm_action_mail(
            claim_url,
            draft.subject,
            reference=draft.reference,
            redirect_url=self.data.get("redirect_url"),
        )

        return draft

    def create_project(self):
        data = self.data
        user = data["user"]

        project = FoiProject(
            title=data["subject"],
            description=data["body"],
            status=FoiProject.STATUS_PENDING,
            public=data["public"],
            user=user,
            site=Site.objects.get_current(),
            reference=data.get("reference", ""),
            language=data.get("language", ""),
            request_count=len(self.data["publicbodies"]),
        )
        save_obj_with_slug(project)
        project.publicbodies.add(*data["publicbodies"])

        if "tags" in data and data["tags"]:
            project.tags.add(*data["tags"])

        FoiProject.project_created.send(sender=project)

        publicbody_ids = [pb.pk for pb in data["publicbodies"]]
        extra = {
            "law_type": data.get("law_type", ""),
            "language": data.get("language", ""),
            "address": data.get("address"),
            "full_text": data.get("full_text", False),
        }
        transaction.on_commit(
            partial(create_project_requests.delay, project.id, publicbody_ids, **extra)
        )
        return project

    def create_request(self, publicbody, sequence=0):
        data = self.data
        user = data["user"]

        now = timezone.now()
        request = FoiRequest(
            title=data["subject"],
            public_body=publicbody,
            user=data["user"],
            description=data["body"],
            public=data["public"],
            language=data.get("language", ""),
            site=Site.objects.get_current(),
            reference=data.get("reference", ""),
            created_at=now,
            last_message=now,
            project=data.get("project"),
            project_order=data.get("project_order"),
        )

        send_now = False

        if not user.is_active:
            request.status = FoiRequest.STATUS.AWAITING_USER_CONFIRMATION
            request.visibility = FoiRequest.VISIBILITY.INVISIBLE
        else:
            request.status = FoiRequest.STATUS.AWAITING_RESPONSE
            request.determine_visibility()
            send_now = True

        request.secret_address = generate_unique_secret_address(user)
        foilaw = None
        if data.get("law_type"):
            law_type = data["law_type"]
            foilaw = publicbody.get_applicable_law(law_type=law_type)

        if foilaw is None:
            foilaw = publicbody.default_law

        request.law = foilaw
        request.jurisdiction = foilaw.jurisdiction

        if send_now:
            request.due_date = request.law.calculate_due_date()

        if data.get("blocked"):
            send_now = False
            request.is_blocked = True

        self.pre_save_request(request)
        save_obj_with_slug(request, count=sequence)

        if "tags" in data and data["tags"]:
            request.tags.add(*[t[:100] for t in data["tags"]])

        subject = "%s [#%s]" % (request.title, request.pk)
        user_replacements = user.get_redactions()
        message = FoiMessage(
            request=request,
            sent=False,
            is_response=False,
            sender_user=user,
            sender_email=request.secret_address,
            sender_name=user.display_name(),
            timestamp=now,
            status="awaiting_response",
            subject=subject,
            subject_redacted=redact_subject(subject, user_replacements),
        )

        proof = self.data.get("proof")
        attachments = []
        attachment_names = []
        if send_now and proof:
            proof_attachment = proof.get_mime_attachment()
            attachment_names.append(proof_attachment[0])
            attachments.append(proof_attachment)

        send_address = bool(self.data.get("address"))
        message.plaintext = construct_initial_message_body(
            request,
            text=data["body"],
            foilaw=foilaw,
            full_text=data.get("full_text", False),
            send_address=send_address,
            attachment_names=attachment_names,
            proof=proof,
        )
        message.plaintext_redacted = redact_plaintext_with_request(
            message.plaintext,
            request,
        )

        message.recipient_public_body = publicbody
        message.recipient = publicbody.name
        message.recipient_email = publicbody.get_email(data.get("law_type"))

        FoiRequest.request_to_public_body.send(sender=request)

        message.save()
        FoiRequest.request_created.send(
            sender=request, reference=data.get("reference", "")
        )
        if send_now:
            message.send(attachments=attachments)
            message.save()
            FoiRequest.message_sent.send(
                sender=request,
                message=message,
            )
            FoiRequest.request_sent.send(
                sender=request, reference=data.get("reference", "")
            )
        return request

    def pre_save_request(self, request):
        pass

    def post_creation(self, foi_object):
        data = self.data
        draft = data.get("draft")
        if draft:
            if isinstance(foi_object, FoiRequest):
                draft.request = foi_object
                draft.project = None
            else:
                draft.project = foi_object
                draft.request = None
            draft.save()


class CreateRequestFromProjectService(CreateRequestService):
    def process(self, request=None):
        data = self.data
        pb = data["publicbody"]
        return self.create_request(pb, sequence=data["project_order"])


class CreateSameAsRequestService(CreateRequestService):
    def create_request(self, publicbody, sequence=0):
        original_request = self.data["original_foirequest"]
        sequence = original_request.same_as_count + 1
        return super().create_request(publicbody, sequence=sequence)

    def pre_save_request(self, request):
        original_request = self.data["original_foirequest"]
        request.same_as = original_request
        request.campaign = original_request.campaign
        request.not_publishable = original_request.not_publishable


class SaveDraftService(BaseService):
    def process(self, request=None):
        data = self.data
        request_form = data["request_form"]
        draft = request_form.cleaned_data.get("draft", None)
        additional_kwargs = dict(
            subject=request_form.cleaned_data.get("subject", ""),
            body=request_form.cleaned_data.get("body", ""),
            full_text=request_form.cleaned_data.get("full_text", False),
            public=request_form.cleaned_data["public"],
            reference=request_form.cleaned_data.get("reference", ""),
            law_type=request_form.cleaned_data.get("law_type", ""),
        )
        if draft is None:
            draft = RequestDraft.objects.create(user=request.user, **additional_kwargs)
        else:
            RequestDraft.objects.filter(id=draft.id).update(**additional_kwargs)
        draft.publicbodies.set(data["publicbodies"])
        return draft


class ReceiveEmailService(BaseService):
    def process(self, request=None):
        foirequest = self.kwargs["foirequest"]
        publicbody = self.kwargs.get("publicbody", None)
        email: ParsedEmail = self.data

        subject = email.subject or ""
        subject = subject[:250]

        message_id = email.message_id or ""
        if message_id:
            message_id = message_id[:512]

        # check if same message has already been delivered
        if message_id:
            message_exists = (
                FoiMessage.objects.filter(request=foirequest)
                .exclude(email_message_id="")
                .filter(email_message_id=message_id)
                .exists()
            )
            if message_exists:
                return

        recipient_name, recipient_email = self.get_recipient_name_email()

        message = FoiMessage(
            request=foirequest,
            subject=subject,
            email_message_id=message_id,
            is_response=True,
            sender_name=email.from_.name,
            sender_email=email.from_.email,
            recipient=recipient_name,
            recipient_email=recipient_email,
            plaintext=email.body,
            html=email.html,
        )

        message.update_email_headers(email)

        is_bounce = email.bounce_info.is_bounce
        if not is_bounce:
            if publicbody is None:
                publicbody = get_publicbody_for_email(message.sender_email, foirequest)
            if publicbody is None:
                publicbody = foirequest.public_body
        else:
            publicbody = None

        message.sender_public_body = publicbody

        message.content_hidden = self.should_hide_content(email, foirequest, publicbody)

        if email.date is None:
            message.timestamp = timezone.now()
        else:
            if email.date < foirequest.first_message:
                # Mail timestamp is earlier than first outgoing message due to bad time on mail server
                message.timestamp = timezone.now()
            else:
                message.timestamp = email.date

        # if the message timestamp is still before or equal first outgoing message
        if message.timestamp <= foirequest.first_message:
            # bump it by one second
            message.timestamp = foirequest.first_message + timedelta(seconds=1)

        user_replacements = foirequest.user.get_redactions()
        message.subject_redacted = redact_subject(message.subject, user_replacements)
        message.plaintext_redacted = redact_plaintext_with_request(
            message.plaintext,
            foirequest,
            redact_closing=True,
        )

        if is_bounce:
            self.process_bounce_message(message)
            return

        message.save()

        if email.is_auto_reply:
            message.tags.add(AUTO_REPLY_TAG)

        if email.fails_authenticity:
            ProblemReport.objects.report(
                message=message,
                kind=ProblemReport.PROBLEM.MAIL_INAUTHENTIC,
                description="\n".join(str(c) for c in email.fails_authenticity),
                auto_submitted=True,
            )

        foirequest._messages = None
        foirequest.status = FoiRequest.STATUS.AWAITING_CLASSIFICATION
        foirequest.save()

        self.add_attachments(foirequest, message, email.attachments)

        foirequest.message_received.send(sender=foirequest, message=message)

    def get_recipient_name_email(self):
        foirequest = self.kwargs["foirequest"]
        email = self.data

        recipient_name, recipient_email = "", ""
        if email.is_direct_recipient(foirequest.secret_address):
            recipient_name = foirequest.user.display_name()
            recipient_email = foirequest.secret_address
        else:
            try:
                recipient_name = email.to[0].name
                recipient_email = email.to[0].email
            except IndexError:
                pass
        return recipient_name, recipient_email

    def should_hide_content(self, email, foirequest, publicbody):
        # Hide auto replies and bounces as they may expose sensitive info
        if email.is_auto_reply or email.bounce_info.is_bounce:
            return True

        # Hide mediatior replies so it stays confidential by default
        if (
            foirequest.law
            and foirequest.law.mediator
            and publicbody == foirequest.law.mediator
            and foirequest.public_body != foirequest.law.mediator
        ):
            return True

        funcs = settings.FROIDE_CONFIG["hide_content_funcs"]
        for func in funcs:
            if func(email):
                return True
        return False

    def process_bounce_message(self, message):
        email = self.data
        foirequest = self.kwargs["foirequest"]

        # Find message
        for sent_message in reversed(foirequest.sent_messages()):
            if (
                sent_message.recipient_email
                and sent_message.recipient_email in message.plaintext
            ):
                break
        else:
            sent_message = None

        message.original = sent_message
        message.save()

        message.tags.add(BOUNCE_TAG)
        if sent_message:
            sent_message.tags.add(HAS_BOUNCED_TAG)

        ProblemReport.objects.report(
            message=sent_message or message,
            kind=ProblemReport.PROBLEM.BOUNCE_PUBLICBODY,
            description=email.bounce_info.diagnostic_code or "",
            auto_submitted=True,
        )

        foirequest._messages = None
        foirequest.save()

        self.add_attachments(foirequest, message, email.attachments)

    def add_attachments(self, foirequest, message, attachments):
        account_service = AccountService(foirequest.user)
        names = set()

        for i, attachment in enumerate(attachments):
            att = FoiAttachment(
                belongs_to=message,
                name=attachment.name,
                size=attachment.size,
                filetype=attachment.content_type,
            )
            if not att.name:
                att.name = _("attached_file_%d") % i

            # Translators: replacement for person name in filename
            repl = str(_("NAME"))
            att.name = account_service.apply_name_redaction(att.name, repl)
            att.name = re.sub(r"[^A-Za-z0-9_\.\-]", "", att.name)
            att.name = att.name[:250]

            # Assure name is unique
            att.name = make_unique_filename(att.name, names)
            names.add(att.name)

            if foirequest.not_publishable:
                att.can_approve = False

            attachment._committed = False
            att.file = File(attachment)
            att.save()

            if att.can_convert_to_pdf():
                self.trigger_convert_pdf(att.id)

    def trigger_convert_pdf(self, att_id):
        transaction.on_commit(partial(convert_attachment_task.delay, att_id))


class ActivatePendingRequestService(BaseService):
    def process(self, request=None):
        if "request_id" in self.data:
            try:
                foirequest = FoiRequest.objects.get(id=self.data["request_id"])
            except FoiRequest.DoesNotExist:
                return None
        else:
            foirequest = self.data["foirequest"]

        if request is not None and request.user != foirequest.user:
            return

        send_now = foirequest.set_status_after_change()
        if send_now and foirequest.law:
            foirequest.due_date = foirequest.law.calculate_due_date()
        foirequest.save()
        if send_now:
            foirequest.safe_send_first_message()
            FoiRequest.request_sent.send(sender=foirequest)
        return foirequest


class ResendBouncedMessageService(BaseService):
    def process(self, request=None):
        message = self.data

        if message.original:
            message.tags.add(BOUNCE_RESENT_TAG)
            return self.resend_message(message.original)

        return self.resend_message(message)

    def resend_message(self, sent_message):
        sent_message.tags.remove(HAS_BOUNCED_TAG)
        foirequest = sent_message.request
        sent_message.recipient_email = foirequest.public_body.email
        sent_message.sent = False
        sent_message.save()
        sent_message.force_resend()
        return sent_message
