import json

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class BounceConfig(AppConfig):
    name = 'froide.bounce'
    verbose_name = _('Bounce')

    def ready(self):
        from froide.account import account_canceled
        from froide.account.export import registry

        account_canceled.connect(cancel_user)
        registry.register(export_user_data)


def cancel_user(sender, user=None, **kwargs):
    from .models import Bounce

    if user is None:
        return
    Bounce.objects.filter(user=user).delete()


def export_user_data(user):
    from .models import Bounce

    bounces = Bounce.objects.filter(user=user)
    if not bounces:
        return
    yield ('bounces.json', json.dumps([
        {
            'last_update': (
                b.last_update.isoformat() if b.last_update else None
            ),
            'bounces': b.bounces,
            'email': b.email,
        }
        for b in bounces]).encode('utf-8')
    )
