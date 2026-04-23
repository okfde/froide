from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AlertConfig(AppConfig):
    name = "froide.searchalert"
    verbose_name = _("Search Alert App")

    def ready(self):
        from froide.account import (
            account_canceled,
            account_email_changed,
            account_merged,
        )
        from froide.account.export import registry
        from froide.bounce.signals import email_unsubscribed

        from .utils import (
            cancel_user,
            email_changed,
            export_user_data,
            handle_unsubscribe,
            merge_user,
        )

        account_canceled.connect(cancel_user)
        account_email_changed.connect(email_changed)
        account_merged.connect(merge_user)
        registry.register(export_user_data)

        email_unsubscribed.connect(handle_unsubscribe)
