from django.db import models

from django_comments.abstracts import CommentAbstractModel


class FroideComment(CommentAbstractModel):
    ip_address = None
    is_moderation = models.BooleanField(default=False)
