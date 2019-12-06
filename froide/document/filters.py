from django import forms
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from taggit.models import Tag
import django_filters

from froide.helper.search.filters import BaseSearchFilterSet
from froide.publicbody.models import PublicBody, Jurisdiction
from froide.campaign.models import Campaign
from froide.account.models import User
from froide.helper.auth import get_read_queryset

from filingcabinet.models import Page

from .models import Document, DocumentCollection


def get_document_read_qs(request):
    return get_read_queryset(
        Document.objects.all(),
        request,
        has_team=True,
        public_field='public',
        scope='read:document'
    )


class PageDocumentFilterset(BaseSearchFilterSet):
    query_fields = ['title^3', 'description^2', 'content']

    campaign = django_filters.ModelChoiceFilter(
        queryset=Campaign.objects.get_filter_list(),
        to_field_name='slug',
        null_value='-',
        empty_label=_('all/no campaigns'),
        null_label=_('no campaign'),
        widget=forms.Select(
            attrs={
                'label': _('campaign'),
                'class': 'form-control'
            }
        ),
        method='filter_campaign'
    )
    jurisdiction = django_filters.ModelChoiceFilter(
        queryset=Jurisdiction.objects.get_visible(),
        to_field_name='slug',
        empty_label=_('all jurisdictions'),
        widget=forms.Select(
            attrs={
                'label': _('jurisdiction'),
                'class': 'form-control'
            }
        ),
        method='filter_jurisdiction'
    )
    tag = django_filters.ModelChoiceFilter(
        queryset=Tag.objects.all(),
        to_field_name='slug',
        method='filter_tag',
        widget=forms.HiddenInput()
    )
    publicbody = django_filters.ModelChoiceFilter(
        queryset=PublicBody._default_manager.all(),
        to_field_name='slug',
        method='filter_publicbody',
        widget=forms.HiddenInput()
    )
    collection = django_filters.ModelChoiceFilter(
        queryset=None,
        to_field_name='pk',
        method='filter_collection',
        widget=forms.HiddenInput()
    )
    document = django_filters.ModelChoiceFilter(
        queryset=None,
        to_field_name='pk',
        method='filter_document',
        widget=forms.HiddenInput()
    )
    user = django_filters.ModelChoiceFilter(
        queryset=User.objects.get_public_profiles(),
        to_field_name='username',
        method='filter_user',
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Page
        fields = [
            'q', 'jurisdiction', 'campaign',
            'tag', 'publicbody', 'collection',
            'number', 'user'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get('request')
        document_qs = get_document_read_qs(request)
        collection_qs = get_read_queryset(
            DocumentCollection.objects.all(), request,
            has_team=True, public_field='public',
            scope='read:document'
        )
        self.filters['collection'].field.queryset = collection_qs
        self.filters['document'].field.queryset = document_qs

    def filter_jurisdiction(self, qs, name, value):
        return qs.filter(jurisdiction=value.id)

    def filter_campaign(self, qs, name, value):
        if value == '-':
            return qs.filter(
                Q('bool', must_not={
                    'exists': {'field': 'campaign'}
                })
            )
        return qs.filter(campaign=value.id)

    def filter_tag(self, qs, name, value):
        return qs.filter(tags=value.id)

    def filter_publicbody(self, qs, name, value):
        return qs.filter(publicbody=value.id)

    def filter_collection(self, qs, name, value):
        return qs.filter(collections=value.id)

    def filter_document(self, qs, name, value):
        return qs.filter(document=value.id)

    def filter_user(self, qs, name, value):
        return qs.filter(user=value.id)
