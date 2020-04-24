import json

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BounceConfig(AppConfig):
    name = 'froide.bounce'
    verbose_name = _('Bounce')

    def ready(self):
        from froide.account import account_canceled
        from froide.account.export import registry

        from froide.helper.email_sending import mail_middleware_registry

        account_canceled.connect(cancel_user)
        registry.register(export_user_data)
        mail_middleware_registry.register(UnsubscribeReferenceMailMiddleware())


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


class UnsubscribeReferenceMailMiddleware:
    '''
    Moves unsubscribe_reference from mail render context
    to email sending kwargs
    '''
    def enhance_email_kwargs(self, mail_intent, context, email_kwargs):
        unsubscribe_reference = context.get('unsubscribe_reference')
        if unsubscribe_reference is None:
            return
        return {
            'unsubscribe_reference': unsubscribe_reference
        }
