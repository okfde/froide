from __future__ import unicode_literals

import hashlib
import re
import hmac

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.db import transaction, IntegrityError
from django.conf import settings
from django.dispatch import Signal
from django.core.mail import send_mail
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.crypto import constant_time_compare
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.six import text_type as str

from froide.helper.text_utils import replace_custom, replace_word

from .models import User


user_activated_signal = Signal(providing_args=[])


class AccountService(object):
    def __init__(self, user):
        self.user = user

    @classmethod
    def get_username_base(self, firstname, lastname):
        base = ""
        first = slugify(firstname)
        last = slugify(lastname)
        if first and last:
            base = "%s.%s" % (first[0], last)
        elif last:
            base = last
        elif first:
            base = first
        else:
            base = "user"
        base = base[:27]
        return base

    @classmethod
    def create_user(cls, **data):
        user = User(first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['user_email'])
        username_base = cls.get_username_base(user.first_name, user.last_name)

        user.is_active = False
        if 'password' in data:
            password = data['password']
        else:
            password = User.objects.make_random_password()
        user.set_password(password)

        user.private = data['private']

        for key in ('address', 'organization', 'organization_url'):
            setattr(user, key, data.get(key, ''))

        # ensure username is unique
        username = username_base
        first_round = True
        count = 0
        postfix = ""
        while True:
            try:
                with transaction.atomic():
                    while True:
                        if not first_round:
                            postfix = "_%d" % count
                        if not User.objects.filter(username=username + postfix).exists():
                            break
                        if first_round:
                            first_round = False
                            count = User.objects.filter(username__startswith=username).count()
                        else:
                            count += 1
                    user.username = username + postfix
                    user.save()
            except IntegrityError:
                pass
            else:
                break

        return user, password

    def confirm_account(self, secret, request_id=None):
        if not self.check_confirmation_secret(secret, request_id):
            return False
        self.user.is_active = True
        self.user.save()
        user_activated_signal.send_robust(sender=self.user)
        return True

    def get_autologin_url(self, url):
        return settings.SITE_URL + reverse('account-go', kwargs={"user_id": self.user.id,
            "secret": self.generate_autologin_secret(),
            "url": url})

    def check_autologin_secret(self, secret):
        return constant_time_compare(self.generate_autologin_secret(), secret)

    def generate_autologin_secret(self):
        to_sign = [str(self.user.pk)]
        if self.user.last_login:
            to_sign.append(self.user.last_login.strftime("%Y-%m-%dT%H:%M:%S"))
        return hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            (".".join(to_sign)).encode('utf-8'),
            digestmod=hashlib.md5
        ).hexdigest()

    def check_confirmation_secret(self, secret, *args):
        return constant_time_compare(
                secret,
                self.generate_confirmation_secret(*args)
        )

    def generate_confirmation_secret(self, *args):
        if self.user.email is None:
            return ''
        to_sign = [str(self.user.pk), self.user.email]
        for a in args:
            to_sign.append(str(a))
        if self.user.last_login:
            to_sign.append(self.user.last_login.strftime("%Y-%m-%dT%H:%M:%S"))
        return hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            (".".join(to_sign)).encode('utf-8'),
            digestmod=hashlib.md5
        ).hexdigest()

    def send_confirmation_mail(self, request_id=None, password=None):
        secret = self.generate_confirmation_secret(request_id)
        url_kwargs = {"user_id": self.user.pk, "secret": secret}
        if request_id:
            url_kwargs['request_id'] = request_id
        url = reverse('account-confirm', kwargs=url_kwargs)
        message = render_to_string('account/confirmation_mail.txt',
                {'url': settings.SITE_URL + url,
                'password': password,
                'name': self.user.get_full_name(),
                'site_name': settings.SITE_NAME,
                'site_url': settings.SITE_URL
            })
        # Translators: Mail subject
        send_mail(str(_("%(site_name)s: please confirm your account") % {
                    "site_name": settings.SITE_NAME}),
                message, settings.DEFAULT_FROM_EMAIL, [self.user.email])

    def send_email_change_mail(self, email):
        secret = self.generate_confirmation_secret(email)
        url_kwargs = {
            "user_id": self.user.pk,
            "secret": secret,
            "email": email
        }
        url = '%s%s?%s' % (
            settings.SITE_URL,
            reverse('account-change_email'),
            urlencode(url_kwargs)
        )
        message = render_to_string('account/change_email.txt',
                {'url': url,
                'name': self.user.get_full_name(),
                'site_name': settings.SITE_NAME,
                'site_url': settings.SITE_URL
            })
        # Translators: Mail subject
        send_mail(str(_("%(site_name)s: please confirm your new email address") % {
                    "site_name": settings.SITE_NAME}),
                message, settings.DEFAULT_FROM_EMAIL, [email])

    def apply_name_redaction(self, content, replacement=''):
        if not self.user.private:
            return content

        needles = [
            self.user.last_name, self.user.first_name,
            self.user.get_full_name()
        ]
        if self.user.organization:
            needles.append(self.user.organization)

        needles = [re.escape(n) for n in needles]

        for needle in needles:
            content = re.sub(needle, replacement, content, flags=re.I | re.U)

        return content

    def apply_message_redaction(self, content, replacements=None):
        if replacements is None:
            replacements = {}

        if self.user.address and replacements.get('address') is not False:
            for line in self.user.address.splitlines():
                if line.strip():
                    content = content.replace(line,
                            replacements.get('address',
                                str(_("<< Address removed >>")))
                    )

        if self.user.email and replacements.get('email') is not False:
            content = content.replace(self.user.email,
                    replacements.get('email',
                    str(_("<< Email removed >>")))
            )

        if not self.user.private or replacements.get('name') is False:
            return content

        name_replacement = replacements.get('name',
                str(_("<< Name removed >>")))

        content = replace_custom(settings.FROIDE_CONFIG['greetings'],
                name_replacement, content)

        content = replace_word(self.user.last_name, name_replacement, content)
        content = replace_word(self.user.first_name, name_replacement, content)
        content = replace_word(self.user.get_full_name(), name_replacement, content)

        if self.user.organization:
            content = replace_word(self.user.organization, name_replacement, content)

        return content
