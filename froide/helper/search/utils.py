from functools import partial

from django.db import transaction

from ..tasks import search_instance_save


def trigger_search_index_update(instance):
    transaction.on_commit(
        partial(search_instance_save.delay, instance._meta.label_lower, instance.pk)
    )


def trigger_search_index_update_qs(queryset):
    for instance in queryset:
        trigger_search_index_update(instance)
