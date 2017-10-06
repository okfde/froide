import hmac
import json

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.utils.six import text_type as str
from django.db import models, transaction, IntegrityError
from django.conf import settings
from django import dispatch
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.crypto import constant_time_compare
from django.utils import timezone
from django.contrib.auth.models import (AbstractBaseUser, PermissionsMixin,
                                        BaseUserManager)
from django.contrib.auth.validators import UnicodeUsernameValidator

from froide.helper.text_utils import replace_custom, replace_word
from froide.helper.csv_utils import export_csv, get_dict

user_activated_signal = dispatch.Signal(providing_args=[])


class UserManager(BaseUserManager):

    def _create_user(self, email, username, password,
                     is_staff, is_superuser, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)

        if not username:
            raise ValueError('The given username must be set')
        username = self.model.normalize_username(username)

        user = self.model(email=email,
                          is_staff=is_staff, is_active=True,
                          is_superuser=is_superuser, last_login=now,
                          date_joined=now, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, username, password=None, **extra_fields):
        return self._create_user(email, username, password, False, False,
                                 **extra_fields)

    def create_superuser(self, email, username, password=None, **extra_fields):
        return self._create_user(email, username, password, True, True,
                                 **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    email = models.EmailField(_('email address'), unique=True, null=True,
                              blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

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

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def get_absolute_url(self):
        if self.private:
            return ""
        return reverse('account-profile', kwargs={'slug': self.username})

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

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

    def as_json(self):
        return json.dumps({
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'address': self.address,
            'private': self.private,
            'email': self.email,
            'organization': self.organization
        })

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

        content = replace_custom(settings.FROIDE_CONFIG['greetings'],
                name_replacement, content)

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
        from django.contrib.auth.forms import SetPasswordForm

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
