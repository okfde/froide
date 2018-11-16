default_app_config = 'froide.comments.apps.CommentConfig'


def get_model():
    from .models import FroideComment
    return FroideComment


def get_form():
    from .forms import CommentForm
    return CommentForm
