from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

User = get_user_model()


def convert_bounce_info(bounce_info):
    d = dict(bounce_info._asdict())
    d["timestamp"] = d["timestamp"].isoformat()
    return d


class BounceManager(models.Manager):
    def update_bounce(self, email, bounce_info):
        email_lower = email.lower()
        try:
            bounce = Bounce.objects.get(email=email_lower)
            bounce.last_update = timezone.now()
            bounce.bounces.append(convert_bounce_info(bounce_info))
            bounce.save()
        except Bounce.DoesNotExist:
            user = None
            users = User.objects.filter(email__iexact=email_lower)
            if len(users) > 1:
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    pass
            if users and not user:
                user = users[0]
            bounce = Bounce.objects.create(
                email=email, user=user, bounces=[convert_bounce_info(bounce_info)]
            )
        return bounce


class EmailTokenManager(models.Manager):
    def _generate_token(cls):
        # lowercase alphabet + digits only, 50 chars long, to be used in local part of email
        # max length of local part is 64 chars, needs space for e.g. 'bounce+' prefix.
        return get_random_string(
            50, allowed_chars="abcdefghijklmnopqrstuvwxyz0123456789"
        )

    def get_token_for_email(self, email):
        email_lower = email.lower()
        contact, _created = self.get_or_create(
            email=email_lower, defaults={"token": self._generate_token()}
        )
        return contact.token

    def get_email_for_token(self, token):
        contact = self.filter(token=token).first()
        return contact.email if contact else None


class EmailToken(models.Model):
    email = models.EmailField(max_length=255, db_index=True, unique=True)
    token = models.CharField(max_length=50, db_index=True, unique=True)
    created = models.DateTimeField(default=timezone.now)

    objects = EmailTokenManager()

    class Meta:
        verbose_name = _("Email Token")
        verbose_name_plural = _("Email Tokens")

    def __str__(self):
        return self.email


class Bounce(models.Model):
    email = models.EmailField(max_length=255)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE
    )
    bounces = models.JSONField(default=list, blank=True)
    last_update = models.DateTimeField(default=timezone.now)

    objects = BounceManager()

    class Meta:
        verbose_name = _("Bounce")
        verbose_name_plural = _("Bounces")

    def __str__(self):
        return "{} ({})".format(self.email, len(self.bounces))
