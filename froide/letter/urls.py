from django.urls import path
from django.utils.translation import gettext_lazy as _

from .views import (
    LetterView, PreviewLetterView,
    SentLetterView
)


urlpatterns = [
    path(_('make-letter/<int:letter_id>/<int:message_id>/'), LetterView.as_view(), name='letter-make'),
    path(_('make-letter/<int:letter_id>/<int:message_id>/preview/'), PreviewLetterView.as_view(), name='letter-preview'),
    path(_('letter-sent/<int:letter_id>/<int:message_id>/'), SentLetterView.as_view(), name='letter-sent'),
]
