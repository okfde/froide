import json

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FoiRequestFollowerConfig(AppConfig):
    name = 'froide.foirequestfollower'
    verbose_name = _('FOI Request Follower')

    def ready(self):
        from froide.account import account_canceled, account_merged
        import froide.foirequestfollower.signals  # noqa
        from froide.account.export import registry

        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        registry.register(export_user_data)


def cancel_user(sender, user=None, **kwargs):
    from .models import FoiRequestFollower

    if user is None:
        return
    FoiRequestFollower.objects.filter(user=user).delete()


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership
    from .models import FoiRequestFollower

    move_ownership(
        FoiRequestFollower, 'user_id', old_user.id, new_user.id,
        dupe=('user_id', 'request_id',)
    )
    # Don't follow your own requests
    # FIXME: this will not work in case foirequest signal has
    # not run yet. Check if order is fix
    FoiRequestFollower.objects.filter(
        user=new_user, request__user=new_user
    ).delete()


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
