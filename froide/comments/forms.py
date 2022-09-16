from django import forms
from django.utils.translation import gettext_lazy as _

from django_comments.forms import COMMENT_MAX_LENGTH
from django_comments.forms import CommentForm as DjangoCommentForm


class CommentForm(DjangoCommentForm):
    name = forms.CharField(
        label=_("Name"),
        required=True,
        max_length=50,
        help_text=_("Your name will only be visible to logged in users."),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    comment = forms.CharField(
        label=_("Comment"),
        widget=forms.Textarea(attrs={"class": "form-control", "rows": "4"}),
        max_length=COMMENT_MAX_LENGTH,
    )
    is_moderation = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        required=False,
        initial=True,
        label=_("This is a moderation comment"),
    )

    def __init__(self, target_object, data=None, initial=None, **kwargs):
        super().__init__(target_object, data=data, initial=initial, **kwargs)
        object_id = self.target_object.id
        for field in self.fields:
            id = "id_{}_{}".format(field, object_id)
            self.fields[field].widget.attrs["id"] = id
