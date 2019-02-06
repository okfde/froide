import json

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class GuideConfig(AppConfig):
    name = 'froide.guide'
    verbose_name = _('Guide')

    def ready(self):
        from .signals import start_guidance_task
        from froide.foirequest.models import FoiRequest
        from froide.account import account_merged
        from froide.account.export import registry

        FoiRequest.message_received.connect(start_guidance_task)

        account_merged.connect(merge_user)
        registry.register(export_user_data)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership
    from .models import Guidance

    move_ownership(Guidance, 'user', old_user, new_user)


def export_user_data(user):
    from .models import Guidance

    guidances = (
        Guidance.objects.filter(user=user)
    )
    if guidances:
        yield ('guidances.json', json.dumps([
            {
                'message': a.message_id,
                'timestamp': a.timestamp.isoformat(),
                'label': a.label,
                'description': a.description,
                'snippet': a.snippet,
            }
            for a in guidances]).encode('utf-8')
        )
