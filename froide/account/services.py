import hashlib
import re
import hmac
from urllib.parse import urlencode

from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils.crypto import constant_time_compare
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from froide.helper.db_utils import save_obj_unique
from froide.helper.email_sending import mail_registry

from .models import User, AccountBlacklist
from . import account_activated


def get_user_for_email(email):
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return False


confirmation_mail = mail_registry.register(
    'account/emails/confirmation_mail',
    ('action_url', 'name', 'request_id')
)
confirm_action_mail = mail_registry.register(
    'account/emails/confirm_action',
    ('title', 'action_url', 'name')
)
reminder_mail = mail_registry.register(
    'account/emails/account_reminder',
    ('name', 'action_url')
)
change_email_mail = mail_registry.register(
    'account/emails/change_email',
    ('action_url', 'name')
)


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
        existing_user = get_user_for_email(data['user_email'])
        if existing_user:
            return existing_user, False

        user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['user_email']
        )
        username_base = cls.get_username_base(user.first_name, user.last_name)

        user.is_active = False
        if 'password' in data:
            user.set_password(data['password'])

        user.private = data['private']

        for key in ('address', 'organization', 'organization_url'):
            setattr(user, key, data.get(key, ''))

        cls.check_against_blacklist(user)

        # ensure username is unique
        user.username = username_base
        save_obj_unique(user, 'username', postfix_format='_{count}')

        return user, True

    def confirm_account(self, secret, request_id=None):
        if not self.check_confirmation_secret(secret, request_id):
            return False
        self._confirm_account()
        return True

    def _confirm_account(self):
        self.user.is_active = True
        self.user.save()
        account_activated.send_robust(sender=self.user)

    def get_autologin_url(self, url):
        return settings.SITE_URL + reverse('account-go', kwargs={
            "user_id": self.user.id,
            "secret": self.generate_autologin_secret(),
            "url": url
        })

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

    def send_confirmation_mail(self, request_id=None, reference=None,
                               redirect_url=None):
        secret = self.generate_confirmation_secret(request_id)
        url_kwargs = {"user_id": self.user.pk, "secret": secret}
        if request_id:
            url_kwargs['request_id'] = request_id
        url = reverse('account-confirm', kwargs=url_kwargs)

        params = {}
        if reference:
            params['ref'] = reference.encode('utf-8')
        if redirect_url:
            params['next'] = redirect_url.encode('utf-8')
        if params:
            url = '%s?%s' % (url, urlencode(params))

        template_base = None
        if reference is not None:
            ref = reference.split(':', 1)[0]
            template_base = 'account/emails/{}/confirmation_mail'.format(
                ref
            )

        context = {
            'action_url': settings.SITE_URL + url,
            'request_id': request_id,
            'name': self.user.get_full_name(),
        }

        confirmation_mail.send(
            user=self.user, context=context,
            template_base=template_base,
            reference=reference,
            ignore_active=True, priority=True
        )

    def send_confirm_action_mail(self, url, title, reference=None,
                                 redirect_url=None):
        secret_url = self.get_autologin_url(url)

        params = {}
        if reference:
            params['ref'] = reference.encode('utf-8')
        if redirect_url:
            params['next'] = redirect_url.encode('utf-8')
        if params:
            secret_url = '%s?%s' % (secret_url, urlencode(params))

        # Translators: Mail subject
        subject = str(_("%(site_name)s: please confirm your action") % {
            "site_name": settings.SITE_NAME
        })

        context = {
            'action_url': secret_url,
            'title': title,
            'name': self.user.get_full_name(),
        }

        confirm_action_mail.send(
            user=self.user, context=context,
            subject=subject,
            priority=True,
            reference=reference
        )

    def send_reminder_mail(self, reference=None, redirect_url=None):
        secret_url = self.get_autologin_url(reverse('account-show'))

        context = {
            'action_url': secret_url,
            'name': self.user.get_full_name(),
        }

        # Translators: Mail subject
        subject = str(_("%(site_name)s: account reminder") % {
            "site_name": settings.SITE_NAME
        })
        reminder_mail.send(
            user=self.user, context=context,
            subject=subject, reference=reference
        )

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
        context = {
            'action_url': url,
            'name': self.user.get_full_name(),
        }
        # Translators: Mail subject
        subject = str(_("%(site_name)s: please confirm your new email address") % {
            "site_name": settings.SITE_NAME
        })
        change_email_mail.send(
            email=email, context=context,
            subject=subject,
            priority=True
        )

    @classmethod
    def check_against_blacklist(cls, user, save=True):
        blacklisted = AccountBlacklist.objects.is_blacklisted(user)
        if blacklisted:
            user.is_blocked = True

            if save:
                user.save()
        return blacklisted

    def apply_name_redaction(self, content, replacement=''):
        if not self.user.private:
            return content

        if self.user.is_deleted:
            # No more info present about user to redact
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

    def get_user_redactions(self, replacements=None):
        if self.user.is_deleted:
            return

        repl = {
            'name': str(_("<< Name removed >>")),
            'email': str(_("<< Email removed >>")),
            'address': str(_("<< Address removed >>")),
        }
        if replacements is not None:
            repl.update(replacements)

        if self.user.address:
            for line in self.user.address.splitlines():
                if line.strip():
                    yield (line.strip(), repl['address'])

        if self.user.email:
            yield (self.user.email, repl['email'])

        if not self.user.private:
            return

        yield (settings.FROIDE_CONFIG['greetings'], repl['name'])
        yield (self.user.last_name, repl['name'])
        yield (self.user.first_name, repl['name'])
        yield (self.user.get_full_name(), repl['name'])

        if self.user.organization:
            yield (self.user.organization, repl['name'])
