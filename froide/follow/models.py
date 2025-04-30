import hashlib
import hmac
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, List, Union

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.dispatch import Signal
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.translation import gettext_lazy as _

from .configuration import FollowConfiguration, follow_registry

User = get_user_model()

REFERENCE_PREFIX = "follow-"
CONFIRM_EMAIL_TIME = timedelta(days=7)

FollowerIdent = Union[User, str]


@dataclass
class FollowerItem:
    section: str
    content_object: Any
    object_label: str
    unfollow_link: str
    events: List[str]


class FollowerManager(models.Manager):
    def is_following(self, content_object, user=None, email=None):
        if email is not None:
            return (
                self.get_queryset()
                .filter(content_object=content_object, email=email, confirmed=True)
                .exists()
            )
        else:
            return (
                self.get_queryset()
                .filter(content_object=content_object, user=user)
                .exists()
            )

    def follow(self, content_object, user, email=None, **extra_data):
        if user.is_authenticated:
            return self.user_follow(content_object, user, extra_data)
        else:
            return self.email_follow(content_object, email, extra_data)

    def user_follow(self, content_object, user, extra_data):
        try:
            follower = self.get_queryset().get(content_object=content_object, user=user)
            follower.unfollowing.send(sender=follower)
            follower.delete()
            return False
        except self.model.DoesNotExist:
            pass
        follower = self.create(
            content_object=content_object,
            user=user,
            confirmed=True,
            context=extra_data or None,
        )
        follower.followed.send(sender=follower)
        return True

    def get_user_for_email(self, email):
        try:
            return User.objects.get(is_active=True, email=email)
        except User.DoesNotExist:
            return None

    def email_follow(self, content_object, email, extra_data):
        try:
            # Existing email follow
            follower = self.get_queryset().get(
                content_object=content_object,
                email=email,
            )
        except self.model.DoesNotExist:
            follower = None

        user = self.get_user_for_email(email)

        if follower is None:
            follower = self.create(
                content_object=content_object, email=email, context=extra_data or None
            )
        follower.send_confirm_follow_mail(extra_data, user=user)
        return True

    def cleanup_unconfirmed_email_follows(self):
        time_ago = timezone.now() - CONFIRM_EMAIL_TIME
        self.get_queryset().exclude(confirmed=True).exclude(user=None).filter(
            timestamp__lt=time_ago
        ).delete()


class Follower(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("User"),
        on_delete=models.CASCADE,
    )
    email = models.CharField(max_length=255, blank=True)
    confirmed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(_("Timestamp of Following"), default=timezone.now)
    context = models.JSONField(blank=True, null=True)

    objects = FollowerManager()

    followed = Signal()  # args: []
    unfollowing = Signal()  # args: []

    class Meta:
        abstract = True
        get_latest_by = "timestamp"
        ordering = ("-timestamp",)
        constraints = [
            models.UniqueConstraint(
                fields=["content_object", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_user_follower_%(app_label)s_%(class)s",
            ),
            models.UniqueConstraint(
                fields=["content_object", "email"],
                condition=models.Q(user__isnull=True),
                name="unique_email_follower_%(app_label)s_%(class)s",
            ),
        ]

    def __str__(self):
        return _("%(user)s follows %(content_object)s") % {
            "user": self.email or str(self.user),
            "content_object": self.content_object,
        }

    def get_full_name(self):
        if self.user:
            return self.user.get_full_name()
        return ""

    def get_email(self):
        if self.user:
            return self.user.email
        return self.email

    @property
    def configuration(self) -> FollowConfiguration:
        return follow_registry.get_by_model(self.__class__)

    def get_context(self):
        return {
            "unsubscribe_url": self.get_unfollow_link(),
            "unsubscribe_reference": "{prefix}{model}-{pk}".format(
                prefix=REFERENCE_PREFIX, model=self._meta.label_lower, pk=self.id
            ),
        }

    def get_ident(self) -> FollowerIdent:
        return self.user or self.email

    def get_unfollow_link(self, user=None):
        return self.get_link(kind="unfollow", user=user)

    def get_follow_link(self, user=None):
        return self.get_link(user=user)

    def get_link(self, kind="follow", user=user):
        url = reverse(
            "follow:confirm_{}".format(kind),
            kwargs={
                "follow_id": self.id,
                "check": self.get_follow_secret(),
                "conf_slug": self.configuration.slug,
            },
        )
        if user is not None:
            return user.get_autologin_url(url)
        return settings.SITE_URL + url

    def get_follow_secret(self):
        to_sign = [
            self.email,
            self.configuration.model_name,
            str(self.content_object.id),
            str(self.id),
        ]
        return hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            (".".join(to_sign)).encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    def check_and_unfollow(self, check):
        secret = self.get_follow_secret()
        if constant_time_compare(check, secret):
            self.unfollowing.send(sender=self)
            self.delete()
            return True
        return False

    def check_and_follow(self, check, request=None):
        secret = self.get_follow_secret()
        if not constant_time_compare(check, secret):
            return False
        if self.confirmed:
            return True
        if self.email:
            user = self.__class__.objects.get_user_for_email(self.email)
            if user is not None and self.configuration.can_follow(
                self.content_object, user
            ):
                already_following = self.__class__.objects.filter(
                    content_object=self.content_object, user=user
                ).exists()
                if already_following:
                    # Remove duplicate
                    self.delete()
                    return True
                self.user = user
                self.email = ""
        self.confirmed = True
        self.save()
        self.followed.send(sender=self, request=request)
        return True

    def send_confirm_follow_mail(self, extra_data, user=None):
        """
        user is unconfirmed, but matches email address if given
        """
        context = {
            "content_object": self.content_object,
            "user": user,
            "confirm_follow_message": self.configuration.get_confirm_follow_message(
                self.content_object
            ),
            "action_url": self.get_follow_link(user=user),
        }
        context.update(extra_data)
        context.update(self.get_context())
        self.configuration.get_follow_email().send(
            email=self.email,
            subject=_("Please confirm notifications for “{title}”").format(
                title=self.content_object
            ),
            context=context,
            priority=True,
        )
