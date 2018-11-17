from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class BounceConfig(AppConfig):
    name = 'froide.bounce'
    verbose_name = _('Bounce')

    def ready(self):
        from froide.account import account_canceled

        account_canceled.connect(cancel_user)


def cancel_user(sender, user=None, **kwargs):
    from .models import Bounce

    if user is None:
        return
    Bounce.objects.filter(user=user).delete()
