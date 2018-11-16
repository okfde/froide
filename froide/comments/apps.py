from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CommentConfig(AppConfig):
    name = 'froide.comments'
    verbose_name = _('Comments')

    def ready(self):
        from froide.account import account_canceled

        account_canceled.connect(cancel_user)


def cancel_user(sender, user=None, **kwargs):
    from .models import FroideComment

    if user is None:
        return
    FroideComment.objects.filter(user=user).update(
        user_name='',
        user_email='',
        user_url=''
    )
