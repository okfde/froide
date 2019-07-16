from django.apps import AppConfig
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _


class FoiRequestConfig(AppConfig):
    name = 'froide.foirequest'
    verbose_name = _('FOI Request')

    def ready(self):
        from froide.account import (
            account_canceled, account_merged, account_made_private
        )
        from froide.account.export import registry
        from froide.helper.search import search_registry
        from django_comments.signals import comment_will_be_posted
        from froide.foirequest import signals  # noqa
        from .utils import (
            cancel_user, merge_user, export_user_data, make_account_private
        )

        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        account_made_private.connect(make_account_private)
        registry.register(export_user_data)
        search_registry.register(add_search)
        comment_will_be_posted.connect(signals.pre_comment_foimessage)


def add_search(request):
    return {
        'title': _('Requests'),
        'name': 'foirequest',
        'url': reverse('foirequest-list')
    }
