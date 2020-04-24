import json

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccessTokenConfig(AppConfig):
    name = 'froide.accesstoken'
    verbose_name = _('Secret Access Token')

    def ready(self):
        from froide.account import account_canceled, account_merged
        from froide.account.export import registry

        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        registry.register(export_user_data)


def cancel_user(sender, user=None, **kwargs):
    from .models import AccessToken

    if user is None:
        return
    AccessToken.objects.filter(user=user).delete()


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership
    from .models import AccessToken

    move_ownership(AccessToken, 'user', old_user, new_user, dupe=('user', 'purpose'))


def export_user_data(user):
    from .models import AccessToken

    access_tokens = (
        AccessToken.objects.filter(user=user)
    )
    if access_tokens:
        yield ('access_tokens.json', json.dumps([
            {
                'purpose': a.purpose,
                'timestamp': a.timestamp.isoformat(),
            }
            for a in access_tokens]).encode('utf-8')
        )
