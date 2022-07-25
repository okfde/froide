from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from taggit.forms import TagField, TagWidget

from froide.helper.auth import get_write_queryset
from froide.helper.text_utils import slugify
from froide.helper.widgets import BootstrapCheckboxInput, BootstrapSelect

from .models import Document, DocumentCollection
from .tasks import store_document_upload


class DocumentUploadForm(forms.Form):
    collection = forms.ModelChoiceField(
        label=_("Add all to collection"), queryset=None, required=False
    )
    collection_title = forms.CharField(
        label=_("Or add all to new collection with this title"),
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text=_("Leave empty and no collection will be created"),
    )

    public = forms.BooleanField(
        initial=True,
        required=False,
        label=_("Make documents public"),
        widget=BootstrapCheckboxInput,
    )
    tags = TagField(
        required=False,
        label=_("Tags"),
        help_text=_("These tags will be applied to all documents."),
        widget=TagWidget(attrs={"class": "form-control"}),
    )
    language = forms.ChoiceField(
        choices=Document.LANGUAGE_CHOICES,
        initial=settings.LANGUAGE_CODE,
        label=_("Language"),
        help_text=_("Choose the dominant language of the documents."),
        widget=BootstrapSelect,
    )

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["collection"].queryset = get_write_queryset(
            DocumentCollection.objects.all(), request, has_team=True
        )

    def save(self, user):
        upload_list = self.data.getlist("upload")
        collection_id = None
        if self.cleaned_data["collection"]:
            collection_id = self.cleaned_data["collection"].id
        elif self.cleaned_data["collection_title"]:
            title = self.cleaned_data["collection_title"]
            collection = DocumentCollection.objects.create(
                title=title,
                slug=slugify(title),
                user=user,
                public=self.cleaned_data["public"],
            )
            collection_id = collection.id

        store_document_upload.delay(
            upload_list, user.id, self.cleaned_data, collection_id
        )
        doc_count = len(upload_list)

        return doc_count
