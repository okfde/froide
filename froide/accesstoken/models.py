import uuid

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class AccessTokenManager(models.Manager):
    def create_for_user(self, user, purpose=None):
        at, created = AccessToken.objects.get_or_create(
            user=user,
            purpose=purpose
        )
        return at.token

    def reset(self, user, purpose=None):
        new_token = uuid.uuid4()
        AccessToken.objects.filter(user=user, purpose=purpose).update(
            token=new_token,
            timestamp=timezone.now()
        )
        return new_token

    def get_token_by_user(self, user, purpose=None):
        at = self.get_by_user(user, purpose=purpose)
        if at is not None:
            return at.token
        return None

    def get_by_user(self, user, purpose=None):
        try:
            return AccessToken.objects.get(
                user=user,
                purpose=purpose
            )
        except AccessToken.DoesNotExist:
            return None

    def get_user_by_token(self, token, purpose=None):
        try:
            return AccessToken.objects.get(
                token=token,
                purpose=purpose
            ).user
        except AccessToken.DoesNotExist:
            return None


class AccessToken(models.Model):
    token = models.UUIDField(
        default=uuid.uuid4, editable=False, db_index=True
    )
    purpose = models.CharField(max_length=30)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(default=timezone.now)

    objects = AccessTokenManager()

    class Meta:
        verbose_name = _('access token')
        verbose_name_plural = _('access tokens')

    def __str__(self):
        return '{} - {}'.format(self.user_id, self.purpose)
