from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from froide.account.models import User


class BounceManager(models.Manager):
    def update_bounce(self, email, bounce_info):
        email = email.lower()
        try:
            bounce = Bounce.objects.get(email=email.lower())
            bounce.last_update = timezone.now()
            bounce.bounces.append(
                dict(bounce_info._asdict())
            )
        except Bounce.DoesNotExist:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                user = None
            bounce = Bounce.objects.create(
                email=email,
                user=user,
                bounces=[dict(bounce_info._asdict())]
            )
        return bounce


class Bounce(models.Model):
    email = models.EmailField(max_length=255)

    user = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.CASCADE
    )
    bounces = JSONField(default=list)
    last_update = models.DateTimeField(default=timezone.now)

    objects = BounceManager()

    class Meta:
        verbose_name = _('Bounce')
        verbose_name_plural = _('Bounces')

    def __str__(self):
        return '{} ({})'.format(self.email, len(self.bounces))
