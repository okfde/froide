from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from froide.account.models import User


def convert_bounce_info(bounce_info):
    d = dict(bounce_info._asdict())
    d['timestamp'] = d['timestamp'].isoformat()
    return d


class BounceManager(models.Manager):
    def update_bounce(self, email, bounce_info):
        email_lower = email.lower()
        try:
            bounce = Bounce.objects.get(email=email_lower)
            bounce.last_update = timezone.now()
            bounce.bounces.append(
                convert_bounce_info(bounce_info)
            )
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
                email=email,
                user=user,
                bounces=[convert_bounce_info(bounce_info)]
            )
        return bounce


class Bounce(models.Model):
    email = models.EmailField(max_length=255)

    user = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.CASCADE
    )
    bounces = JSONField(default=list, blank=True)
    last_update = models.DateTimeField(default=timezone.now)

    objects = BounceManager()

    class Meta:
        verbose_name = _('Bounce')
        verbose_name_plural = _('Bounces')

    def __str__(self):
        return '{} ({})'.format(self.email, len(self.bounces))
