from django.db import models

from django_comments.abstracts import CommentAbstractModel
from django_comments.signals import comment_will_be_posted


class FroideComment(CommentAbstractModel):
    ip_address = None
    comment_as_normal_user = models.BooleanField(null=True)


def set_comment_as_normal_user_flag(comment, **kwargs):
    normal_user = kwargs.get("request").POST.get("comment_as_normal_user") == "on"
    comment.comment_as_normal_user = normal_user


comment_will_be_posted.connect(set_comment_as_normal_user_flag)
