import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AccessTokenManager(models.Manager):
    def create_for_user(self, user, purpose):
        at, created = AccessToken.objects.get_or_create(user=user, purpose=purpose)
        return at.token

    def reset(self, user, purpose):
        new_token = uuid.uuid4()
        AccessToken.objects.filter(user=user, purpose=purpose).update(
            token=new_token, timestamp=timezone.now()
        )
        return new_token

    def get_token_by_user(self, user, purpose):
        at = self.get_by_user(user, purpose=purpose)
        if at is not None:
            return at.token
        return None

    def get_by_user(self, user, purpose):
        try:
            return AccessToken.objects.get(user=user, purpose=purpose)
        except AccessToken.DoesNotExist:
            return None

    def get_by_token(self, token, purpose):
        try:
            return AccessToken.objects.get(token=token, purpose=purpose)
        except AccessToken.DoesNotExist:
            return None

    def get_user_by_token(self, token, purpose):
        access_token = self.get_by_token(token, purpose=purpose)
        if access_token:
            return access_token.user
        return None


class AccessToken(models.Model):
    token = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    purpose = models.CharField(max_length=30)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)

    objects = AccessTokenManager()

    class Meta:
        verbose_name = _("access token")
        verbose_name_plural = _("access tokens")

    def __str__(self):
        return "{} - {}".format(self.user_id, self.purpose)
