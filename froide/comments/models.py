from django.db import models

from django_comments.abstracts import CommentAbstractModel
from django_comments.signals import comment_will_be_posted

from froide.foirequest.auth import can_moderate_foirequest


class FroideComment(CommentAbstractModel):
    ip_address = None
    is_moderation = models.BooleanField(default=False)


def set_is_moderation_flag(comment, **kwargs):
    is_moderation = False
    request = kwargs.get("request")
    foi_request = comment.content_object.request
    if can_moderate_foirequest(foi_request, request):
        is_moderation = request.POST.get("is_moderation") == "on"
    comment.is_moderation = is_moderation


comment_will_be_posted.connect(set_is_moderation_flag)
