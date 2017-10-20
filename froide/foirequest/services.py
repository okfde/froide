from __future__ import unicode_literals

from django.db import transaction, IntegrityError
from django.utils import timezone
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify

from froide.account.models import AccountManager

from .models import FoiRequest, FoiMessage
from .utils import generate_secret_address, construct_message_body
from .hooks import registry


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
            user, password = AccountManager.create_user(**self.data)
            self.data['user'] = user

        if request is not None:
            extra = registry.run_hook('pre_request_creation',
                request,
                user=user,
                data=data
            )
            data.update(extra)

        foirequest = self.create_request(self.data['publicbodies'][0])

        if user_created:
            AccountManager(user).send_confirmation_mail(
                request_id=foirequest.pk,
                password=password
            )
        return foirequest

    def create_request(self, publicbody, sequence=0):
        data = self.data
        user = data['user']

        now = timezone.now()
        request = FoiRequest(title=data['subject'],
                public_body=publicbody,
                user=data['user'],
                description=data['body'],
                public=data['public'],
                site=Site.objects.get_current(),
                reference=data.get('reference', ''),
                first_message=now,
                last_message=now)

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
        self.save_request_with_slug(request, count=sequence)

        message = FoiMessage(request=request,
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
        FoiRequest.request_created.send(sender=request, reference=data.get('reference', ''))
        if send_now:
            message.send()
            message.save()
        return request

    def pre_save_request(self, request):
        pass

    def save_request_with_slug(self, request, count=0):
        request.slug = slugify(request.title)
        first_round = count == 0
        postfix = ''
        while True:
            try:
                with transaction.atomic():
                    while True:
                        if not first_round:
                            postfix = '-%d' % count
                        if not FoiRequest.objects.filter(
                                slug=request.slug + postfix).exists():
                            break
                        if first_round:
                            first_round = False
                            count = FoiRequest.objects.filter(
                                    slug__startswith=request.slug).count()
                        else:
                            count += 1
                    request.slug += postfix
                    request.save()
            except IntegrityError:
                pass
            else:
                break


class CreateSameAsRequestService(CreateRequestService):
    def pre_save_request(self, request):
        request.same_as = self.data['original_foirequest']
