from django import forms
from django.utils.translation import ugettext_lazy as _

from django_comments.forms import (
    CommentForm as DjangoCommentForm,
    COMMENT_MAX_LENGTH
)


class CommentForm(DjangoCommentForm):
    comment = forms.CharField(
        label=_('Comment'),
        help_text=_(
            'Your comment will be published with your'
            ' registered name visible.'
        ),
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': '4'
            }
        ),
        max_length=COMMENT_MAX_LENGTH
    )
