from django_comments.abstracts import CommentAbstractModel


class FroideComment(CommentAbstractModel):
    ip_address = None

    class Meta(CommentAbstractModel.Meta):
        db_table = "django_comments"
