from __future__ import unicode_literals

import re

from django.db import IntegrityError
from django.utils import timezone
from django.contrib.sites.models import Site
from django.core.files import File
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import slugify

from froide.account.services import AccountService
from froide.helper.text_utils import redact_subject, redact_plaintext
from froide.helper.storage import add_number_to_filename

from .models import (
    FoiRequest, FoiMessage, RequestDraft, FoiProject, FoiAttachment
)
from .utils import (
    generate_secret_address, construct_initial_message_body,
    get_publicbody_for_email
)
from .hooks import registry
from .tasks import create_project_requests


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
        user = data['user']
        user_created = False

        if not user.is_authenticated:
            user_created = True
            user, password = AccountService.create_user(**self.data)
            self.data['user'] = user

        if request is not None:
            extra = registry.run_hook('pre_request_creation',
                request,
                user=user,
                data=data
            )
            if extra is not None:
                data.update(extra)

        if len(self.data['publicbodies']) > 1:
            foi_object = self.create_project()
        else:
            foi_object = self.create_request(self.data['publicbodies'][0])

            if user_created:
                AccountService(user).send_confirmation_mail(
                    request_id=foi_object.pk,
                    password=password,
                    reference=foi_object.reference,
                    redirect_url=self.data.get('redirect_url')
                )
        self.post_creation(foi_object)
        return foi_object

    def create_project(self):
        data = self.data
        user = data['user']

        project = FoiProject(
            title=data['subject'],
            description=data['body'],
            status=FoiProject.STATUS_PENDING,
            public=data['public'],
            user=user,
            site=Site.objects.get_current(),
            reference=data.get('reference', ''),
            request_count=len(self.data['publicbodies'])
        )

        self.save_obj_with_slug(project)
        project.publicbodies.add(*data['publicbodies'])

        if 'tags' in data and data['tags']:
            project.tags.add(*data['tags'])

        FoiProject.project_created.send(sender=project)

        publicbody_ids = [pb.pk for pb in data['publicbodies']]
        extra = {
            'full_text': data.get('full_text', False)
        }
        create_project_requests.delay(
            project.id, publicbody_ids, **extra
        )
        return project

    def create_request(self, publicbody, sequence=0):
        data = self.data
        user = data['user']

        now = timezone.now()
        request = FoiRequest(
            title=data['subject'],
            public_body=publicbody,
            user=data['user'],
            description=data['body'],
            public=data['public'],
            site=Site.objects.get_current(),
            reference=data.get('reference', ''),
            first_message=now,
            last_message=now,
            project=data.get('project'),
            project_order=data.get('project_order'),
        )

        send_now = False

        if not user.is_active:
            request.status = 'awaiting_user_confirmation'
            request.visibility = FoiRequest.INVISIBLE
        else:
            # TODO add draft
            request.status = 'awaiting_response'
            request.determine_visibility()
            send_now = True

        request.secret_address = generate_unique_secret_address(user)
        foilaw = None
        if data.get('law_type'):
            law_type = data['law_type']
            foilaw = publicbody.get_applicable_law(law_type=law_type)

        if foilaw is None:
            foilaw = publicbody.default_law

        request.law = foilaw
        request.jurisdiction = foilaw.jurisdiction

        if send_now:
            request.due_date = request.law.calculate_due_date()

        if data.get('blocked'):
            send_now = False
            request.is_blocked = True

        self.pre_save_request(request)
        self.save_obj_with_slug(request, count=sequence)

        if 'tags' in data and data['tags']:
            request.tags.add(*data['tags'])

        subject = '%s [#%s]' % (request.title, request.pk)
        message = FoiMessage(
            request=request,
            sent=False,
            is_response=False,
            sender_user=user,
            sender_email=request.secret_address,
            sender_name=user.display_name(),
            timestamp=now,
            status='awaiting_response',
            subject=subject,
            subject_redacted=redact_subject(subject, user=user)
        )

        send_address = True
        if request.law:
            send_address = not request.law.email_only

        message.plaintext = construct_initial_message_body(
                request,
                text=data['body'],
                foilaw=foilaw,
                full_text=data.get('full_text', False),
                send_address=send_address)

        message.plaintext_redacted = redact_plaintext(
            message.plaintext,
            is_response=False,
            user=user
        )

        message.recipient_public_body = publicbody
        message.recipient = publicbody.name
        message.recipient_email = publicbody.email

        FoiRequest.request_to_public_body.send(sender=request)

        message.save()
        FoiRequest.request_created.send(
            sender=request,
            reference=data.get('reference', '')
        )
        if send_now:
            message.send()
            message.save()
        return request

    def pre_save_request(self, request):
        pass

    def post_creation(self, foi_object):
        data = self.data
        draft = data.get('draft')
        if draft:
            if isinstance(foi_object, FoiRequest):
                draft.request = foi_object
                draft.project = None
            else:
                draft.project = foi_object
                draft.request = None
            draft.save()

    def save_obj_with_slug(self, obj, attribute='title', count=0):
        MAX_COUNT = 10000000  # max 10 million loops
        obj.slug = slugify(getattr(obj, attribute))
        first_round = count == 0
        postfix = ''
        while True:
            try:
                while count < MAX_COUNT:
                    if not first_round:
                        postfix = '-%d' % count
                    if not FoiRequest.objects.filter(
                            slug=obj.slug + postfix).exists():
                        break
                    if first_round:
                        first_round = False
                        count = FoiRequest.objects.filter(
                                slug__startswith=obj.slug).count()
                    else:
                        count += 1
                obj.slug += postfix
                obj.save()
            except IntegrityError:
                if count < MAX_COUNT:
                    first_round = False
                    count = FoiRequest.objects.filter(
                            slug__startswith=obj.slug).count()
                else:
                    raise
            else:
                break


class CreateRequestFromProjectService(CreateRequestService):
    def process(self, request=None):
        data = self.data
        pb = data['publicbody']
        return self.create_request(pb, sequence=data['project_order'])


class CreateSameAsRequestService(CreateRequestService):
    def pre_save_request(self, request):
        request.same_as = self.data['original_foirequest']


class SaveDraftService(BaseService):
    def process(self, request=None):
        data = self.data
        request_form = data['request_form']
        draft = request_form.cleaned_data.get('draft', None)
        additional_kwargs = dict(
            subject=request_form.cleaned_data.get('subject', ''),
            body=request_form.cleaned_data.get('body', ''),
            full_text=request_form.cleaned_data['full_text'],
            public=request_form.cleaned_data['public'],
            reference=request_form.cleaned_data.get('reference', ''),
            law_type=request_form.cleaned_data.get('law_type', ''),
        )
        if draft is None:
            draft = RequestDraft.objects.create(
                user=request.user,
                **additional_kwargs
            )
        else:
            RequestDraft.objects.filter(id=draft.id).update(
                **additional_kwargs
            )
        draft.publicbodies.set(data['publicbodies'])
        return draft


class ReceiveEmailService(BaseService):

    def process(self, request=None):
        foirequest = self.kwargs['foirequest']
        publicbody = self.kwargs.get('publicbody', None)
        email = self.data

        subject = email['subject'] or ''
        subject = subject[:250]

        message_id = email.get('message_id', '') or ''
        if message_id:
            message_id = message_id[:512]

        message = FoiMessage(
            request=foirequest,
            subject=subject,
            email_message_id=message_id,
            is_response=True,
            sender_name=email['from'][0],
            sender_email=email['from'][1],
            recipient_email=foirequest.secret_address,
            recipient=foirequest.user.display_name(),
            plaintext=email['body'],
            html=email['html'],
            content_hidden=email.get('is_auto_reply', False)
        )

        if publicbody is None:
            publicbody = get_publicbody_for_email(
                message.sender_email, foirequest
            )
        if publicbody is None:
            publicbody = foirequest.public_body

        message.sender_public_body = publicbody

        if foirequest.law and publicbody == foirequest.law.mediator:
            message.content_hidden = True

        if email['date'] is None:
            message.timestamp = timezone.now()
        else:
            message.timestamp = email['date']

        message.subject_redacted = redact_subject(
            message.subject, user=foirequest.user
        )
        message.plaintext_redacted = redact_plaintext(
            message.plaintext, is_response=True,
            user=foirequest.user
        )
        message.save()

        foirequest._messages = None
        foirequest.status = 'awaiting_classification'
        foirequest.last_message = message.timestamp
        foirequest.save()

        self.add_attachments(foirequest, message, email['attachments'])

        foirequest.message_received.send(sender=foirequest, message=message)

    def add_attachments(self, foirequest, message, attachments):
        account_service = AccountService(foirequest.user)
        names = set()

        for i, attachment in enumerate(attachments):
            att = FoiAttachment(
                belongs_to=message,
                name=attachment.name,
                size=attachment.size,
                filetype=attachment.content_type
            )
            if not att.name:
                att.name = _("attached_file_%d") % i

            # Translators: replacement for person name in filename
            repl = str(_('NAME'))
            att.name = account_service.apply_name_redaction(att.name, repl)
            att.name = re.sub(r'[^A-Za-z0-9_\.\-]', '', att.name)
            att.name = att.name[:250]

            # Assure name is unique
            if att.name in names:
                att.name = add_number_to_filename(att.name, i)
            names.add(att.name)

            attachment._committed = False
            att.file = File(attachment)
            att.save()
