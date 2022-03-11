from django.utils.translation import gettext_lazy as _

from froide.helper.notifications import Event

from .models import FroideComment


class CommentEvent(Event):
    def __init__(self, comment: FroideComment):
        self.comment = comment

    def as_text(self):
        return _("New comment by {name}").format(name=self.comment.user_name)

    def as_html(self):
        return ""


def make_event(comment: FroideComment):
    return CommentEvent(comment)
