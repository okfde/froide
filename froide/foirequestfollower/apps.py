from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FoiRequestFollowerConfig(AppConfig):
    name = 'froide.foirequestfollower'
    verbose_name = _('FOI Request Follower')

    def ready(self):
        from froide.account import account_canceled
        import froide.foirequestfollower.signals  # noqa

        account_canceled.connect(cancel_user)


def cancel_user(sender, user=None, **kwargs):
    from .models import FoiRequestFollower

    if user is None:
        return
    FoiRequestFollower.objects.filter(user=user).delete()
