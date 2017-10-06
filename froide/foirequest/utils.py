import random
from datetime import timedelta

from django.utils import timezone
from django.utils.six import string_types
from django.core.mail import mail_managers
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

from froide.helper.date_utils import format_seconds


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
            mail_managers(_('User exceeded request limit'), user.pk)
            return _('You exceeded your request limit of {count} requests in {time}.'
                    ).format(count=throttle_kind[0],
                             time=format_seconds(throttle_kind[1])
            )


def generate_secret_address(user, length=10):
    possible_chars = 'abcdefghkmnprstuvwxyz2345689'
    username = user.username.replace('_', '.')
    secret = "".join([random.choice(possible_chars) for i in range(length)])
    template = getattr(settings, 'FOI_EMAIL_TEMPLATE', None)

    domains = settings.FOI_EMAIL_DOMAIN
    if isinstance(domains, string_types):
        domains = [domains]
    FOI_EMAIL_DOMAIN = domains[0]

    if template is not None and callable(template):
        return settings.FOI_EMAIL_TEMPLATE(username=username, secret=secret)
    elif template is not None:
        return settings.FOI_EMAIL_TEMPLATE.format(username=username,
                                                  secret=secret,
                                                  domain=FOI_EMAIL_DOMAIN)
    return "%s.%s@%s" % (username, secret, FOI_EMAIL_DOMAIN)


def construct_message_body(foirequest, text='', foilaw=None, full_text=False,
                           send_address=True,
                           template='foirequest/emails/foi_request_mail.txt'):
    if full_text:
        body = text
    else:
        letter_start, letter_end = '', ''
        if foilaw:
            letter_start = foilaw.letter_start
            letter_end = foilaw.letter_end
        body = (
            u"{letter_start}\n\n{body}\n\n{letter_end}"
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
