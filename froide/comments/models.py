from django_comments.abstracts import CommentAbstractModel


class FroideComment(CommentAbstractModel):
    ip_address = None
