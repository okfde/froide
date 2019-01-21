import json

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ProblemConfig(AppConfig):
    name = 'froide.problem'
    verbose_name = _('Problems')

    def ready(self):
        from froide.account.export import registry

        from . import signals  # noqa

        registry.register(export_user_data)


def export_user_data(user):
    from .models import ProblemReport

    problems = ProblemReport.objects.filter(
        user=user
    ).select_related('message', 'message__request')
    if not problems:
        return
    yield ('problem_reports.json', json.dumps([
        {
            'message': pb.message.get_absolute_domain_short_url(),
            'timestamp': pb.timestamp.isoformat(),
            'resolved': pb.resolved,
            'kind': pb.get_kind_detail(),
            'description': pb.description,
            'resolution': pb.resolution,
            'resolution_timestamp': (
                pb.resolution_timestamp.isoformat()
                if pb.resolution_timestamp else None
            ),
        }
        for pb in problems]).encode('utf-8')
    )
