import hmac
import re
import urllib

from django.db import models, transaction, IntegrityError
from django.conf import settings
from django import dispatch
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib.auth.forms import SetPasswordForm
from django.utils.crypto import constant_time_compare


@dispatch.receiver(post_save, sender=User, dispatch_uid="account.models.create_profile")
def create_profile(sender, instance=None, created=False, **kwargs):
    if created and not kwargs.get('raw', False):
        Profile.objects.create(user=instance)

user_activated_signal = dispatch.Signal(providing_args=[])


class Profile(models.Model):
    user = models.OneToOneField(User)
    organization = models.CharField(blank=True, max_length=255)
    organization_url = models.URLField(blank=True, max_length=255)
    private = models.BooleanField(default=False)
    address = models.TextField(blank=True)

    def __unicode__(self):
        return unicode(_(u"Profile of <%(user)s>") % {"user": self.user})

    def get_absolute_url(self):
        if self.private:
            return ""
        return reverse('account-profile', kwargs={'slug': self.user.username})

    def display_name(self):
        if self.private:
            return unicode(_(u"Name Not Public"))
        else:
            if self.organization:
                return u'%s (%s)' % (self.user.get_full_name(), self.organization)
            else:
                return self.user.get_full_name()

    def apply_message_redaction(self, content, replacements=None):
        if replacements is None:
            replacements = {}

        if self.address and replacements.get('address') is not False:
            for line in self.address.splitlines():
                if line.strip():
                    content = content.replace(line,
                            replacements.get('address',
                                unicode(_("<< Address removed >>")))
                    )

        if self.user.email and replacements.get('email') is not False:
            content = content.replace(self.user.email,
                    replacements.get('email',
                    unicode(_("<< Email removed >>")))
            )

        if not self.private or replacements.get('name') is False:
            return content

        last_name = self.user.last_name
        first_name = self.user.first_name
        full_name = self.user.get_full_name()

        name_replacement = replacements.get('name',
                unicode(_("<< Name removed >>")))

        content = content.replace(full_name, name_replacement)
        content = content.replace(last_name, name_replacement)
        content = content.replace(first_name, name_replacement)
        if self.organization:
            content = content.replace(self.organization, name_replacement)

        greeting_replacement = replacements.get('greeting',
                unicode(_("<< Greeting >>")))

        if settings.FROIDE_CONFIG.get('greetings'):
            for greeting in settings.FROIDE_CONFIG['greetings']:
                match = greeting.search(content, re.I)
                if match is not None and len(match.groups()):
                    content = content.replace(match.group(1),
                        greeting_replacement)

        if settings.FROIDE_CONFIG.get('closings'):
            for closing in settings.FROIDE_CONFIG['closings']:
                match = closing.search(content, re.I)
                if match is not None:
                    content = content[:match.end()]

        return content

    def get_autologin_url(self, url):
        account_manager = AccountManager(self.user)
        return account_manager.get_autologin_url(url)

    def get_password_change_form(self, *args, **kwargs):
        return SetPasswordForm(self.user, *args, **kwargs)

    def get_address_change_form(self, *args, **kwargs):
        from froide.account.forms import UserChangeAddressForm
        return UserChangeAddressForm(self, *args, **kwargs)


class AccountManager(object):
    def __init__(self, user):
        self.user = user

    @classmethod
    def get_username_base(self, firstname, lastname):
        base = u""
        first = slugify(firstname)
        last = slugify(lastname)
        if first and last:
            base = u"%s.%s" % (first[0], last)
        elif last:
            base = last
        elif first:
            base = first
        else:
            base = u"user"
        base = base[:27]
        return base

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
        return hmac.new(settings.SECRET_KEY, ".".join(to_sign)).hexdigest()

    def check_confirmation_secret(self, secret, *args):
        return constant_time_compare(
                secret,
                self.generate_confirmation_secret(*args)
        )

    def generate_confirmation_secret(self, *args):
        to_sign = [str(self.user.pk), self.user.email]
        for a in args:
            to_sign.append(str(a))
        if self.user.last_login:
            to_sign.append(self.user.last_login.strftime("%Y-%m-%dT%H:%M:%S"))
        return hmac.new(settings.SECRET_KEY, ".".join(to_sign)).hexdigest()

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
        send_mail(unicode(_("%(site_name)s: please confirm your account") % {
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
            urllib.urlencode(url_kwargs)
        )
        message = render_to_string('account/change_email.txt',
                {'url': url,
                'name': self.user.get_full_name(),
                'site_name': settings.SITE_NAME,
                'site_url': settings.SITE_URL
            })
        # Translators: Mail subject
        send_mail(unicode(_("%(site_name)s: please confirm your new email address") % {
                    "site_name": settings.SITE_NAME}),
                message, settings.DEFAULT_FROM_EMAIL, [email])

    @classmethod
    def create_user(cls, **data):
        user = User(first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['user_email'])
        username_base = cls.get_username_base(user.first_name, user.last_name)

        user.is_active = False
        if "password" in data:
            password = data['password']
        else:
            password = User.objects.make_random_password()
        user.set_password(password)

        # ensure username is unique
        while True:
            username = username_base
            first_round = True
            count = 0
            postfix = ""
            with transaction.commit_manually():
                try:
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
                    transaction.rollback()
                else:
                    transaction.commit()
                    break

        profile = user.get_profile()
        for key in data:
            if key in ('first_name', 'last_name', 'user_email', 'password'):
                continue
            setattr(profile, key, data[key])
        profile.save()
        return user, password
