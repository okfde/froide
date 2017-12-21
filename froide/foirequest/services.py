from __future__ import unicode_literals

from django.db import transaction, IntegrityError
from django.utils import timezone
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify

from froide.account.services import AccountService

from .models import FoiRequest, FoiMessage, RequestDraft, FoiProject
from .utils import generate_secret_address, construct_message_body
from .hooks import registry
from .tasks import create_project_requests


class BaseService(object):
    def __init__(self, data):
        self.data = data

    def execute(self, request=None):
        with transaction.atomic():
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
            data.update(extra)

        if len(self.data['publicbodies']) > 1:
            foi_object = self.create_project()
        else:
            foi_object = self.create_request(self.data['publicbodies'][0])

            if user_created:
                AccountService(user).send_confirmation_mail(
                    request_id=foi_object.pk,
                    password=password
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
        if 'tags' in data and data['tags']:
            project.tags.add(*data['tags'])

        FoiProject.project_created.send(sender=project)

        publicbody_ids = [pb.pk for pb in data['publicbodies']]
        create_project_requests.delay(
            project.id, publicbody_ids,
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

        message = FoiMessage(
            request=request,
            sent=False,
            is_response=False,
            sender_user=user,
            sender_email=request.secret_address,
            sender_name=user.display_name(),
            timestamp=now,
            status='awaiting_response',
            subject='%s [#%s]' % (request.title, request.pk)
        )
        message.subject_redacted = message.redact_subject()

        send_address = True
        if request.law:
            send_address = not request.law.email_only

        message.plaintext = construct_message_body(
                request,
                text=data['body'],
                foilaw=foilaw,
                full_text=data.get('full_text', False),
                send_address=send_address)
        message.plaintext_redacted = message.redact_plaintext()

        message.recipient_public_body = publicbody
        message.recipient = publicbody.name
        message.recipient_email = publicbody.email

        FoiRequest.request_to_public_body.send(sender=request)

        message.original = ''
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
        obj.slug = slugify(getattr(obj, attribute))
        first_round = count == 0
        postfix = ''
        while True:
            try:
                with transaction.atomic():
                    while True:
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
                pass
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
        if draft is None:
            draft = RequestDraft.objects.create(
                user=request.user,
                subject=request_form.cleaned_data.get('subject', ''),
                body=request_form.cleaned_data.get('body', ''),
                full_text=request_form.cleaned_data['full_text'],
                public=request_form.cleaned_data['public'],
                reference=request_form.cleaned_data.get('reference', ''),
            )
        else:
            RequestDraft.objects.filter(id=draft.id).update(
                subject=request_form.cleaned_data.get('subject', ''),
                body=request_form.cleaned_data.get('body', ''),
                full_text=request_form.cleaned_data['full_text'],
                public=request_form.cleaned_data['public'],
                reference=request_form.cleaned_data.get('reference', ''),
            )
        draft.publicbodies.set(data['publicbodies'])
        return draft
