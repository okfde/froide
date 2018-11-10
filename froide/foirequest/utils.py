import random
from datetime import timedelta

from django.utils import timezone
from django.core.mail import mail_managers
from django.conf import settings
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

import icalendar
import pytz

from froide.helper.date_utils import format_seconds
from froide.account.utils import send_mail_user


MAX_ATTACHMENT_SIZE = settings.FROIDE_CONFIG['max_attachment_size']


def throttle(qs, throttle_config, date_param='first_message'):
    if throttle_config is None:
        return False

    # Return True if the next request would break any limit
    for count, seconds in throttle_config:
        f = {
            '%s__gte' % date_param: timezone.now() - timedelta(seconds=seconds)
        }
        if qs.filter(**f).count() + 1 > count:
            return (count, seconds)
    return False


def check_throttle(user, klass):
    if user.is_authenticated and not user.trusted():
        throttle_settings = settings.FROIDE_CONFIG.get('request_throttle', None)
        qs, date_param = klass.objects.get_throttle_filter(user)
        throttle_kind = throttle(qs, throttle_settings, date_param=date_param)
        if throttle_kind:
            mail_managers(_('User exceeded request limit'), str(user.pk))
            message = _('You exceeded your request limit of %(count)s requests in %(time)s.')
            return forms.ValidationError(
                message,
                params={
                    'count': throttle_kind[0],
                    'time': format_seconds(throttle_kind[1])
                },
                code='throttled'
            )


def generate_secret_address(user, length=10):
    possible_chars = 'abcdefghkmnprstuvwxyz2345689'
    username = user.username.replace('_', '.')
    secret = "".join([random.choice(possible_chars) for i in range(length)])
    template = getattr(settings, 'FOI_EMAIL_TEMPLATE', None)

    domains = settings.FOI_EMAIL_DOMAIN
    if isinstance(domains, str):
        domains = [domains]
    FOI_EMAIL_DOMAIN = domains[0]

    if template is not None and callable(template):
        return settings.FOI_EMAIL_TEMPLATE(username=username, secret=secret)
    elif template is not None:
        return settings.FOI_EMAIL_TEMPLATE.format(username=username,
                                                  secret=secret,
                                                  domain=FOI_EMAIL_DOMAIN)
    return "%s.%s@%s" % (username, secret, FOI_EMAIL_DOMAIN)


def construct_message_body(foirequest, text, send_address=True,
                           attachment_names=None, attachment_missing=None,
                           template='foirequest/emails/mail_with_userinfo.txt'):
    return render_to_string(
        template,
        {
            'request': foirequest,
            'body': text,
            'attachment_names': attachment_names,
            'attachment_missing': attachment_missing,
            'send_address': send_address
        }
    )


def construct_initial_message_body(
        foirequest, text='', foilaw=None, full_text=False, send_address=True,
        template='foirequest/emails/foi_request_mail.txt'):
    if full_text:
        body = text
    else:
        letter_start, letter_end = '', ''
        if foilaw:
            letter_start = foilaw.letter_start
            letter_end = foilaw.letter_end
        body = (
            "{letter_start}\n\n{body}\n\n{letter_end}"
        ).format(
            letter_start=letter_start,
            body=text,
            letter_end=letter_end
        )

    return render_to_string(template, {
        'request': foirequest,
        'body': body,
        'send_address': send_address
    })


def strip_subdomains(domain):
    return '.'.join(domain.split('.')[-2:])


def get_host(email):
    if email and '@' in email:
        return email.rsplit('@', 1)[1].lower()
    return None


def get_domain(email):
    host = get_host(email)
    if host is None:
        return None
    return strip_subdomains(host)


def compare_publicbody_email(email, foi_request,
                                 transform=lambda x: x.lower()):
    email = transform(email)

    if foi_request.public_body and foi_request.public_body.email:
        pb_value = transform(foi_request.public_body.email)
        if email == pb_value:
            return foi_request.public_body

        mediator = foi_request.public_body.get_mediator()
        if mediator is not None:
            mediator_value = transform(mediator.email)
            if email == mediator_value:
                return mediator

    message_checks = (
        ('sender', foi_request.response_messages()),
        ('recipient', foi_request.sent_messages()),
    )
    for kind, messages in message_checks:
        for message in messages:
            message_email = getattr(message, '%s_email' % kind)
            message_pb = getattr(message, '%s_public_body' % kind)
            if not message_email or not message_pb:
                continue
            message_email = transform(message_email)
            if email == message_email:
                return message_pb


def get_publicbody_for_email(email, foi_request, include_deferred=False):
    if not email:
        return None

    # Compare email direct
    pb = compare_publicbody_email(email, foi_request)
    if pb is not None:
        return pb

    # Compare email full host
    pb = compare_publicbody_email(email, foi_request, transform=get_host)
    if pb is not None:
        return pb

    # Compare email domain without subdomains
    pb = compare_publicbody_email(email, foi_request, transform=get_domain)
    if pb is not None:
        return pb

    # Search in all PublicBodies
    from froide.publicbody.models import PublicBody

    email_host = get_host(email)
    if email_host is None:
        return None
    pbs = PublicBody.objects.filter(email__endswith=email_host)
    if len(pbs) == 1:
        return pbs[0]
    elif foi_request.public_body in pbs:
        # likely the request's public body
        return foi_request.public_body

    if include_deferred:
        from .models import DeferredMessage

        pb = DeferredMessage.objects.get_publicbody_for_email(email)
        if pb is not None:
            return pb

    return None


def send_request_user_email(foiobject, subject, body, add_idmark=True, **kwargs):
    if not foiobject.user:
        return
    if add_idmark:
        subject = '{} [#{}]'.format(subject, foiobject.pk)
    send_mail_user(subject, body, foiobject.user, **kwargs)


class MailAttachmentSizeChecker():
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


def cancel_user(sender, user=None, **kwargs):
    from .models import FoiRequest, RequestDraft

    if user is None:
        return

    FoiRequest.objects.delete_private_requests(user)
    RequestDraft.objects.filter(user=user).delete()

    permanently_anonymize_requests(
        FoiRequest.objects.filter(user=user).select_related('user')
    )


def permanently_anonymize_requests(foirequests):
    from .models import FoiAttachment

    replacements = {
        'name': str(_('<information-removed>')),
        'email': str(_('<information-removed>')),
        'address': str(_('<information-removed>')),
    }
    foirequests.update(
        closed=True
    )
    for foirequest in foirequests:
        user = foirequest.user
        user.private = True
        account_service = user.get_account_service()
        for message in foirequest.messages:
            message.plaintext_redacted = account_service.apply_message_redaction(
                message.plaintext_redacted
            )
            message.plaintext = account_service.apply_message_redaction(
                message.plaintext, replacements=replacements
            )
            message.html = ''
            if message.is_response:
                # This may occasionally delete real sender name
                # when user was only in CC
                message.recipient = ''
            else:
                message.sender_name = ''

            message.save()

        # Delete original attachments, if they have a redacted version
        FoiAttachment.objects.filter(
            approved=False,
            can_approve=False,
            belongs_to__request=foirequest,
            redacted__isnull=False,
            is_redacted=False
        ).delete()


def add_ical_events(foirequest, cal):
    event_timezone = pytz.timezone(settings.TIME_ZONE)

    def tz(x):
        return x.astimezone(event_timezone)

    uid = 'event-%s-{pk}@{domain}'.format(
        pk=foirequest.id, domain=settings.SITE_URL.split('/')[-1])

    title = '{} [#{}]'.format(foirequest.title, foirequest.pk)
    url = settings.SITE_URL + foirequest.get_absolute_url()

    event = icalendar.Event()
    event.add('uid', uid % 'request')
    event.add('dtstamp', tz(timezone.now()))
    event.add('dtstart', tz(foirequest.first_message))
    event.add('url', url)
    event.add('summary', title)
    event.add('description', foirequest.description)
    cal.add_component(event)

    if foirequest.due_date:
        event = icalendar.Event()
        event.add('uid', uid % 'duedate')
        event.add('dtstamp', tz(timezone.now()))
        event.add('dtstart', tz(foirequest.due_date).date())
        event.add('url', url)
        event.add('summary', _('Due date: %s') % title)
        event.add('description', foirequest.description)
        cal.add_component(event)

    if foirequest.status == 'awaiting_response' and (
            foirequest.resolution in ('partially_successful', 'refused')):

        responses = foirequest.response_messages
        if responses:
            appeal_deadline = foirequest.law.calculate_due_date(
                date=responses[-1].timestamp
            )
            event = icalendar.Event()
            event.add('uid', uid % 'appeal_deadline')
            event.add('dtstamp', tz(timezone.now()))
            event.add('dtstart', tz(appeal_deadline).date())
            event.add('url', url)
            event.add('summary', _('Appeal deadline: %s') % title)
            event.add('description', foirequest.description)
            alarm = icalendar.Alarm()
            alarm.add('trigger', icalendar.prop.vDuration(-timedelta(days=1)))
            alarm.add('action', 'DISPLAY')
            alarm.add('description', _('Appeal deadline: %s') % title)
            event.add_component(alarm)
            cal.add_component(event)
