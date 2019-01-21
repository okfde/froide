import json

from django.db.models import Q

from .models import PublicBody


def export_user_data(user):
    pbs = PublicBody.objects.filter(
        Q(_created_by=user) |
        Q(_updated_by=user)
    )
    if not pbs:
        return
    yield ('publicbodies.json', json.dumps([
        {
            'created': pb._created_by_id == user.id,
            'updated': pb._updated_by_id == user.id,
            'created_timestamp': (
                pb.created_at.isoformat() if pb._created_by_id == user.id
                else None),
            'updated_timestamp': (
                pb.updated_at.isoformat() if pb._updated_by_id == user.id
                else None
            ),
            'url': pb.get_absolute_domain_short_url()
        }
        for pb in pbs]).encode('utf-8')
    )
