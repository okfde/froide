import json

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CommentConfig(AppConfig):
    name = "froide.comments"
    verbose_name = _("Comments")

    def ready(self):
        from django_comments.signals import comment_will_be_posted

        from froide.account import account_canceled, account_merged
        from froide.account.export import registry

        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        registry.register(export_user_data)
        comment_will_be_posted.connect(set_is_moderation_flag)


def cancel_user(sender, user=None, **kwargs):
    from .models import FroideComment

    if user is None:
        return
    FroideComment.objects.filter(user=user).update(
        user_name="", user_email="", user_url=""
    )


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from .models import FroideComment

    FroideComment.objects.filter(user=old_user).update(user=new_user)


def export_user_data(user):
    from .models import FroideComment

    comments = FroideComment.objects.filter(user=user)
    if not comments:
        return
    yield (
        "comments.json",
        json.dumps(
            [
                {
                    "user_name": c.user_name,
                    "submit_date": (
                        c.submit_date.isoformat() if c.submit_date else None
                    ),
                    "comment": c.comment,
                    "is_public": c.is_public,
                    "is_removed": c.is_removed,
                    "url": c.get_absolute_url(),
                }
                for c in comments
            ]
        ).encode("utf-8"),
    )


def set_is_moderation_flag(comment, **kwargs):
    from froide.foirequest.auth import can_moderate_foirequest
    from froide.foirequest.models import FoiMessage

    is_moderation = False
    request = kwargs.get("request")
    if isinstance(comment.content_object, FoiMessage):
        foi_request = comment.content_object.request
        if can_moderate_foirequest(foi_request, request):
            is_moderation = request.POST.get("is_moderation") == "on"
        comment.is_moderation = is_moderation
