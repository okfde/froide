from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AccessTokenConfig(AppConfig):
    name = 'froide.accesstoken'
    verbose_name = _('Secret Access Token')

    def ready(self):
        from froide.account import account_canceled

        account_canceled.connect(cancel_user)


def cancel_user(sender, user=None, **kwargs):
    from .models import AccessToken

    if user is None:
        return
    AccessToken.objects.filter(user=user).delete()
