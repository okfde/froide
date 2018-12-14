from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AccountConfig(AppConfig):
    name = 'froide.account'
    verbose_name = _("Account")

    def ready(self):
        from froide.bounce.signals import user_email_bounced

        user_email_bounced.connect(deactivate_user_after_bounce)


def deactivate_user_after_bounce(sender, bounce, should_deactivate=False, **kwargs):
    if not should_deactivate:
        return
    if not bounce.user:
        return
    bounce.user.deactivate()
