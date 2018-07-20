from __future__ import unicode_literals

import json
import os

from django.db import models
from django.utils.six import text_type as str
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import (AbstractBaseUser, PermissionsMixin,
                                        BaseUserManager)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.encoding import python_2_unicode_compatible
from django.conf import settings

from oauth2_provider.models import AbstractApplication

from froide.helper.csv_utils import export_csv, get_dict
from froide.helper.storage import HashedFilenameStorage


def has_newsletter():
    return settings.FROIDE_CONFIG.get("have_newsletter", False)


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


def profile_photo_path(instance=None, filename=None):
    path = ['profile', filename]
    return os.path.join(*path)


@python_2_unicode_compatible
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

    profile_text = models.TextField(blank=True)
    profile_photo = models.ImageField(
        null=True, blank=True,
        upload_to=profile_photo_path,
        storage=HashedFilenameStorage()
    )

    is_trusted = models.BooleanField(_('Trusted'), default=False)
    is_blocked = models.BooleanField(_('Blocked'), default=False)

    is_deleted = models.BooleanField(_('deleted'), default=False,
            help_text=_('Designates whether this user was deleted.'))
    date_left = models.DateTimeField(_('date left'), default=None, null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        if self.email is None:
            return self.username
        return self.email

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

    def show_newsletter(self):
        return has_newsletter() and not self.newsletter

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
            return str(_("<< Name Not Public >>"))
        else:
            if self.organization:
                return '%s (%s)' % (self.get_full_name(), self.organization)
            else:
                return self.get_full_name()

    def get_account_service(self):
        from .services import AccountService

        return AccountService(self)

    def get_autologin_url(self, url):
        from .services import AccountService

        service = AccountService(self)
        return service.get_autologin_url(url)

    def get_password_change_form(self, *args, **kwargs):
        from .forms import SetPasswordForm
        return SetPasswordForm(self, *args, **kwargs)

    def get_change_form(self, *args, **kwargs):
        from .forms import UserChangeForm
        return UserChangeForm(self, *args, **kwargs)


class Application(AbstractApplication):
    description = models.TextField(blank=True)
    homepage = models.CharField(max_length=255, blank=True)
    image_url = models.CharField(max_length=255, blank=True)
    auto_approve_scopes = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True, null=True)
    updated = models.DateTimeField(auto_now=True, null=True)

    def allows_grant_type(self, *grant_types):
        # only allow GRANT_AUTHORIZATION_CODE, GRANT_IMPLICIT
        # regardless of application setting
        return bool(set([
            AbstractApplication.GRANT_AUTHORIZATION_CODE,
            AbstractApplication.GRANT_IMPLICIT
        ]) & set(grant_types))

    def can_auto_approve(self, scopes):
        """
        Check if the token allows the provided scopes

        :param scopes: An iterable containing the scopes to check
        """
        if not scopes:
            return True

        provided_scopes = set(self.auto_approve_scopes.split())
        resource_scopes = set(scopes)

        return resource_scopes.issubset(provided_scopes)
