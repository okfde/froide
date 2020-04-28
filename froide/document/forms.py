from django import forms
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.conf import settings

from taggit.forms import TagField, TagWidget

from filingcabinet.models import CollectionDocument

from froide.upload.models import Upload
from froide.helper.widgets import BootstrapCheckboxInput

from .tasks import move_upload_to_document
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
        collection = None
        if self.cleaned_data['collection_title']:
            collection = DocumentCollection.objects.create(
                title=self.cleaned_data['collection_title'],
                user=user,
                public=self.cleaned_data['public']
            )
        doc_count = len(upload_list)
        for upload_url in upload_list:
            document = self.create_document_from_upload(user, upload_url)
            if document is None:
                continue
            if self.cleaned_data['tags']:
                document.tags.set(*self.cleaned_data['tags'])
            if collection:
                CollectionDocument.objects.get_or_create(
                    collection=collection,
                    document=document
                )

        return doc_count

    def create_document_from_upload(self, user, upload_url):
        upload = Upload.objects.get_by_url(
            upload_url, user=user
        )
        if upload is None:
            return

        document = Document.objects.create(
            title=upload.filename,
            user=user,
            public=self.cleaned_data['public']
        )
        upload.ensure_saving()
        upload.save()

        transaction.on_commit(
            lambda: move_upload_to_document.delay(
                document.id, upload.id
            )
        )
        return document
