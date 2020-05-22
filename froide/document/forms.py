from django import forms
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from taggit.forms import TagField, TagWidget

from froide.helper.widgets import BootstrapCheckboxInput

from .tasks import store_document_upload
from .models import Document, DocumentCollection


class DocumentUploadForm(forms.Form):
    collection_title = forms.CharField(
        label=_('Add all to collection with this title'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        }),
        help_text=_('Leave empty and no collection will be created')
    )
    public = forms.BooleanField(
        initial=True,
        required=False,
        label=_('Make documents public'),
        widget=BootstrapCheckboxInput,
    )
    tags = TagField(
        required=False,
        label=_('Tags'),
        help_text=_('These tags will be applied to all documents.'),
        widget=TagWidget(attrs={
            'class': 'form-control'
        })
    )
    language = forms.ChoiceField(
        choices=Document.LANGUAGE_CHOICES,
        initial=settings.LANGUAGE_CODE,
        label=_('Language'),
        help_text=_('Choose the dominant language of the documents.'),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    def save(self, user):
        upload_list = self.data.getlist('upload')
        collection_id = None
        if self.cleaned_data['collection_title']:
            collection = DocumentCollection.objects.create(
                title=self.cleaned_data['collection_title'],
                user=user,
                public=self.cleaned_data['public']
            )
            collection_id = collection.id

        store_document_upload.delay(
            upload_list,
            user.id,
            self.cleaned_data,
            collection_id
        )
        doc_count = len(upload_list)

        return doc_count
