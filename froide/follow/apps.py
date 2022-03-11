from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FollowConfig(AppConfig):
    name = "froide.follow"
    verbose_name = _("Follow App")

    def ready(self):
        from froide.account import (
            account_canceled,
            account_email_changed,
            account_merged,
        )
        from froide.account.export import registry
        from froide.bounce.signals import email_bounced, email_unsubscribed

        from .utils import (
            cancel_user,
            email_changed,
            export_user_data,
            handle_bounce,
            handle_unsubscribe,
            merge_user,
        )

        account_canceled.connect(cancel_user)
        account_email_changed.connect(email_changed)
        account_merged.connect(merge_user)
        registry.register(export_user_data)

        email_bounced.connect(handle_bounce)
        email_unsubscribed.connect(handle_unsubscribe)
