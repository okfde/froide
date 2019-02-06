import json

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FrontpageConfig(AppConfig):
    name = 'froide.frontpage'
    verbose_name = _('Featured Request')

    def ready(self):
        from froide.account import account_canceled, account_merged
        from froide.account.export import registry

        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        registry.register(export_user_data)


def cancel_user(sender, user=None, **kwargs):
    from .models import FeaturedRequest

    if user is None:
        return
    FeaturedRequest.objects.filter(user=user).update(user=None)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership
    from .models import FeaturedRequest

    move_ownership(FeaturedRequest, 'user', old_user, new_user)


def export_user_data(user):
    from .models import FeaturedRequest

    featured_requests = (
        FeaturedRequest.objects.filter(user=user)
    )
    if featured_requests:
        yield ('featured_requests.json', json.dumps([
            {
                'request': a.request_id,
                'timestamp': a.timestamp.isoformat(),
                'title': a.title,
                'text': a.text,
                'url': a.url,
            }
            for a in featured_requests]).encode('utf-8')
        )
