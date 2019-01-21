import json

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FoiRequestFollowerConfig(AppConfig):
    name = 'froide.foirequestfollower'
    verbose_name = _('FOI Request Follower')

    def ready(self):
        from froide.account import account_canceled
        import froide.foirequestfollower.signals  # noqa
        from froide.account.export import registry

        account_canceled.connect(cancel_user)
        registry.register(export_user_data)


def cancel_user(sender, user=None, **kwargs):
    from .models import FoiRequestFollower

    if user is None:
        return
    FoiRequestFollower.objects.filter(user=user).delete()


def export_user_data(user):
    from .models import FoiRequestFollower
    from froide.foirequest.models.request import get_absolute_domain_short_url

    following = FoiRequestFollower.objects.filter(
        user=user
    )
    if not following:
        return
    yield ('followed_requests.json', json.dumps([
        {
            'timestamp': frf.timestamp.isoformat(),
            'url': get_absolute_domain_short_url(frf.request_id),
        }
        for frf in following]).encode('utf-8')
    )
