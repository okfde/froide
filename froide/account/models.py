import json
import os
import re

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.postgres.fields import CIEmailField
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from oauth2_provider.models import AbstractApplication
from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase

from froide.helper.csv_utils import export_csv, get_dict
from froide.helper.storage import HashedFilenameStorage


class UserTag(TagBase):
    public = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("user tag")
        verbose_name_plural = _("user tags")


class TaggedUser(TaggedItemBase):
    tag = models.ForeignKey(
        UserTag, on_delete=models.CASCADE, null=True, related_name="tagged_users"
    )
    content_object = models.ForeignKey("User", on_delete=models.CASCADE)
    count = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = _("tagged user")
        verbose_name_plural = _("tagged users")


class UserManager(BaseUserManager):
    def get_public_profiles(self):
        return super().get_queryset().filter(is_active=True, private=False)

    def _create_user(
        self, email, username, password, is_staff, is_superuser, **extra_fields
    ):
        """
        Creates and saves a User with the given email and password.
        """
        now = timezone.now()
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)

        if not username:
            raise ValueError("The given username must be set")
        username = self.model.normalize_username(username)

        user = self.model(
            email=email,
            username=username,
            is_staff=is_staff,
            is_active=True,
            is_superuser=is_superuser,
            last_login=None,
            date_joined=now,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, username, password=None, **extra_fields):
        return self._create_user(
            email, username, password, False, False, **extra_fields
        )

    def create_superuser(self, email, username, password=None, **extra_fields):
        return self._create_user(email, username, password, True, True, **extra_fields)


def profile_photo_path(instance=None, filename=None):
    path = ["profile", filename]
    return os.path.join(*path)


class User(AbstractBaseUser, PermissionsMixin):

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_("first name"), max_length=30, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    email = CIEmailField(_("email address"), unique=True, null=True, blank=True)

    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    organization_name = models.CharField(
        _("Organization"),
        blank=True,
        max_length=255,
        help_text=_("Optional. Affiliation will be shown next to your name"),
    )
    organization_url = models.URLField(
        _("Organization Website"), blank=True, max_length=255
    )

    language = models.CharField(
        verbose_name=_("Language"),
        max_length=10,
        default=settings.LANGUAGE_CODE,
        choices=settings.LANGUAGES,
        help_text=_("Determines the default language of communication with you."),
    )

    private = models.BooleanField(_("Private"), default=False)
    address = models.TextField(_("Address"), blank=True)
    terms = models.BooleanField(_("Accepted Terms"), default=True)

    profile_text = models.TextField(blank=True)
    profile_photo = models.ImageField(
        null=True,
        blank=True,
        upload_to=profile_photo_path,
        storage=HashedFilenameStorage(),
    )

    is_trusted = models.BooleanField(_("Trusted"), default=False)
    is_blocked = models.BooleanField(_("Blocked"), default=False)

    date_deactivated = models.DateTimeField(
        _("date deactivated"), default=None, null=True, blank=True
    )
    is_deleted = models.BooleanField(
        _("deleted"),
        default=False,
        help_text=_("Designates whether this user was deleted."),
    )
    date_left = models.DateTimeField(
        _("date left"), default=None, null=True, blank=True
    )

    tags = TaggableManager(through=TaggedUser, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    backend = settings.AUTHENTICATION_BACKENDS[0]

    def __str__(self):
        if self.email is None:
            return self.username
        return self.email

    def get_absolute_url(self):
        if self.private:
            return ""
        if not self.username:
            return ""
        return reverse("account-profile", kwargs={"slug": self.username})

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def get_dict(self, fields):
        d = get_dict(self, fields)
        if "request_count" in fields:
            d["request_count"] = self.foirequest_set.all().count()
        return d

    def trusted(self):
        return self.is_trusted or self.is_staff or self.is_superuser

    @classmethod
    def export_csv(cls, queryset, fields=None):
        if fields is None:
            fields = (
                "id",
                "first_name",
                "last_name",
                "email",
                "organization",
                "organization_url",
                "private",
                "date_joined",
                "is_staff",
                "address",
                "terms",
                "request_count",
                ("tags", lambda x: ",".join(str(t) for t in x.tags.all())),
            )
        return export_csv(queryset, fields)

    def as_json(self):
        return json.dumps(
            {
                "id": self.id,
                "first_name": self.first_name,
                "last_name": self.last_name,
                "address": self.address,
                "private": self.private,
                "email": self.email,
                "organization": self.organization_name,
            }
        )

    def display_name(self):
        if self.private:
            return str(_("<< Name Not Public >>"))
        else:
            if self.organization_name:
                return "%s (%s)" % (self.get_full_name(), self.organization_name)
            else:
                return self.get_full_name()

    def get_account_service(self):
        from .services import AccountService

        return AccountService(self)

    def get_autologin_url(self, url="/"):
        from .services import AccountService

        service = AccountService(self)
        return service.get_autologin_url(url)

    def get_redactions(self, replacements=None):
        account_service = self.get_account_service()
        return list(account_service.get_user_redactions(replacements))

    def get_password_change_form(self, *args, **kwargs):
        from .forms import SetPasswordForm

        return SetPasswordForm(self, *args, **kwargs)

    def get_change_form(self, *args, **kwargs):
        from .forms import UserChangeDetailsForm

        return UserChangeDetailsForm(self, *args, **kwargs)

    def get_profile_form(self, *args, **kwargs):
        from .forms import ProfileForm

        return ProfileForm(*args, instance=self, **kwargs)

    def get_account_settings_form(self, *args, **kwargs):
        from .forms import AccountSettingsForm

        return AccountSettingsForm(*args, instance=self, **kwargs)

    def send_mail(self, subject, body, **kwargs):
        from .utils import send_mail_user

        return send_mail_user(subject, body, self, **kwargs)

    def deactivate(self):
        from .utils import delete_all_unexpired_sessions_for_user

        delete_all_unexpired_sessions_for_user(self)

        self.is_active = False
        self.date_deactivated = timezone.now()
        self.save()

    def deactivate_and_block(self):
        self.is_blocked = True
        self.deactivate()


class Application(AbstractApplication):
    description = models.TextField(blank=True)
    homepage = models.CharField(max_length=255, blank=True)
    image_url = models.CharField(max_length=255, blank=True)
    auto_approve_scopes = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True, null=True)
    updated = models.DateTimeField(auto_now=True, null=True)

    def allows_grant_type(self, *grant_types):
        # only allow GRANT_AUTHORIZATION_CODE
        # regardless of application setting
        return bool(
            set([AbstractApplication.GRANT_AUTHORIZATION_CODE]) & set(grant_types)
        )

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


class AccountBlocklistManager(models.Manager):
    def is_blocklisted(self, user):
        if user.is_blocked:
            return True

        for entry in AccountBlocklist.objects.all():
            match = entry.match_user(user)
            if match:
                return True
        return False

    def should_block_address(self, address):
        for entry in AccountBlocklist.objects.all():
            match = entry.match_content(entry.address, address)
            if match:
                return True
        return False


class AccountBlocklist(models.Model):
    name = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(default=timezone.now)

    address = models.TextField(blank=True)
    email = models.TextField(blank=True)

    objects = AccountBlocklistManager()

    class Meta:
        verbose_name = _("Blocklist entry")
        verbose_name_plural = _("Blocklist")

    def __str__(self):
        return self.name

    def match_user(self, user):
        return self.match_field(user, "address") or self.match_field(user, "email")

    def match_field(self, user, key):
        content = getattr(self, key)
        value = getattr(user, key)
        return self.match_content(content, value)

    def match_content(self, content, value):
        if not content:
            return False
        for line in content.splitlines():
            match = re.search(line, value, re.I | re.S)
            if match:
                return True
        return False


class UserPreferenceManager(models.Manager):
    def get_preference(self, user, key):
        try:
            return self.get_queryset().get(user=user, key=key).value
        except UserPreference.DoesNotExist:
            return None

    def get_preferences(self, user, key_prefix=None):
        condition = {}
        if key_prefix:
            condition = {"key__startswith": key_prefix}
        return {
            x.key: x.value for x in self.get_queryset().filter(user=user, **condition)
        }


class UserPreference(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now=True)
    value = models.JSONField()

    objects = UserPreferenceManager()

    class Meta:
        verbose_name = _("User preference")
        verbose_name_plural = _("User preferences")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "key"], name="unique_user_preference_key"
            )
        ]

    def __str__(self):
        return "{} ({})".format(self.key, self.user)
