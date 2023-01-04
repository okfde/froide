from functools import partial

from django.db import transaction
from django.utils.http import urlencode

from ..tasks import search_instance_save


def get_pagination_vars(data):
    d = data.copy()
    d.pop("page", None)
    return "&" + urlencode(d)


def trigger_search_index_update(instance):
    transaction.on_commit(
        partial(search_instance_save.delay, instance._meta.label_lower, instance.pk)
    )


def trigger_search_index_update_qs(queryset):
    for instance in queryset:
        trigger_search_index_update(instance)
