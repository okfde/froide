import hmac

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from uuid import uuid4

from django.utils.six import text_type as str
from django.db import models, transaction, IntegrityError
from django.conf import settings
from django import dispatch
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.crypto import constant_time_compare
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import AbstractUser, UserManager

from froide.helper.text_utils import replace_greetings, replace_word
from froide.helper.csv_utils import export_csv, get_dict

user_activated_signal = dispatch.Signal(providing_args=[])


class User(AbstractUser):
    organization = models.CharField(_('Organization'), blank=True, max_length=255)
    organization_url = models.URLField(_('Organization URL'), blank=True, max_length=255)
    private = models.BooleanField(_('Private'), default=False)
    address = models.TextField(_('Address'), blank=True)
    terms = models.BooleanField(_('Accepted Terms'), default=True)
    newsletter = models.BooleanField(_('Wants Newsletter'), default=False)

    is_trusted = models.BooleanField(_('Trusted'), default=False)
    is_blocked = models.BooleanField(_('Blocked'), default=False)

    is_deleted = models.BooleanField(_('deleted'), default=False,
            help_text=_('Designates whether this user was deleted.'))
    date_left = models.DateTimeField(_('date left'), default=None, null=True, blank=True)

    objects = UserManager()

    feed_access_token = models.CharField(_('feed access key'), default=uuid4().hex, blank=True, max_length=40)
    # if settings.CUSTOM_AUTH_USER_MODEL_DB:
    #     class Meta:
    #         db_table = settings.CUSTOM_AUTH_USER_MODEL_DB

    def get_absolute_url(self):
        if self.private:
            return ""
        return reverse('account-profile', kwargs={'slug': self.username})

    def get_dict(self, fields):
        d = get_dict(self, fields)
        d['request_count'] = self.foirequest_set.all().count()
        return d

    def trusted(self):
        return self.is_trusted or self.is_staff or self.is_superuser

    @classmethod
    def export_csv(cls, queryset):
        fields = (
            "id", "first_name", "last_name", "email",
            "organization", "organization_url", "private",
            "date_joined", "is_staff",
            "address", "terms", "newsletter",
            "request_count",
        )
        return export_csv(queryset, fields)

    def display_name(self):
        if self.private:
            return str(_(u"<< Name Not Public >>"))
        else:
            if self.organization:
                return u'%s (%s)' % (self.get_full_name(), self.organization)
            else:
                return self.get_full_name()

    def apply_message_redaction(self, content, replacements=None):
        if replacements is None:
            replacements = {}

        if self.address and replacements.get('address') is not False:
            for line in self.address.splitlines():
                if line.strip():
                    content = content.replace(line,
                            replacements.get('address',
                                str(_("<< Address removed >>")))
                    )

        if self.email and replacements.get('email') is not False:
            content = content.replace(self.email,
                    replacements.get('email',
                    str(_("<< Email removed >>")))
            )

        if not self.private or replacements.get('name') is False:
            return content

        name_replacement = replacements.get('name',
                str(_("<< Name removed >>")))

        content = replace_greetings(content,
                settings.FROIDE_CONFIG['greetings'],
                name_replacement)

        content = replace_word(self.last_name, name_replacement, content)
        content = replace_word(self.first_name, name_replacement, content)
        content = replace_word(self.get_full_name(), name_replacement, content)

        if self.organization:
            content = replace_word(self.organization, name_replacement, content)

        return content

    def get_autologin_url(self, url):
        account_manager = AccountManager(self)
        return account_manager.get_autologin_url(url)

    def get_password_change_form(self, *args, **kwargs):
        return SetPasswordForm(self, *args, **kwargs)

    def get_change_form(self, *args, **kwargs):
        from froide.account.forms import UserChangeForm
        return UserChangeForm(self, *args, **kwargs)


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
        return hmac.new(
                settings.SECRET_KEY.encode('utf-8'),
                (".".join(to_sign)).encode('utf-8')
        ).hexdigest()

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
        return hmac.new(
                settings.SECRET_KEY.encode('utf-8'),
                (".".join(to_sign)).encode('utf-8')
        ).hexdigest()

    def generate_new_feed_token(self):
        self.user.feed_access_token = uuid4().hex
        self.user.save()

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
