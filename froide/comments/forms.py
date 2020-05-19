from django import forms
from django.utils.translation import gettext_lazy as _

from django_comments.forms import (
    CommentForm as DjangoCommentForm,
    COMMENT_MAX_LENGTH
)


class CommentForm(DjangoCommentForm):
    name = forms.CharField(
        label=_('Name'),
        required=True,
        help_text=_('Your name will only be visible to logged in users.'),
        widget=forms.TextInput(
            attrs={
                'class': 'form-control'
            }
        )
    )
    comment = forms.CharField(
        label=_('Comment'),
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': '4'
            }
        ),
        max_length=COMMENT_MAX_LENGTH
    )
