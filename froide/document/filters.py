from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from taggit.models import Tag
import django_filters

from froide.helper.search.filters import BaseSearchFilterSet
from froide.publicbody.models import PublicBody, Jurisdiction
from froide.campaign.models import Campaign
from froide.account.models import User
from froide.helper.auth import get_read_queryset

from filingcabinet.models import DocumentPortal, Page

from .models import Document, DocumentCollection


def get_document_read_qs(request, detail=False):
    public_q = Q(public=True, listed=True)
    if detail:
        public_q = Q(public=True)
    return get_read_queryset(
        Document.objects.all(),
        request,
        has_team=True,
        public_q=public_q,
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
        queryset=DocumentCollection.objects.all(),
        to_field_name='pk',
        method='filter_collection',
        widget=forms.HiddenInput()
    )
    portal = django_filters.ModelChoiceFilter(
        queryset=DocumentPortal.objects.filter(public=True),
        to_field_name='pk',
        method='filter_portal',
        widget=forms.HiddenInput()
    )
    document = django_filters.ModelChoiceFilter(
        queryset=Document.objects.all(),
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
    number = django_filters.NumberFilter(
        method='filter_number',
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Page
        fields = [
            'q', 'jurisdiction', 'campaign',
            'tag', 'publicbody', 'collection',
            'number', 'user', 'portal'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get('request')
        if request is None:
            request = self.view.request
        self.request = request

    def filter_queryset(self, queryset):
        required_unlisted_filters = {'document', 'collection'}
        filter_present = any(
            v for k, v in self.form.cleaned_data.items()
            if k in required_unlisted_filters
        )
        if not filter_present:
            queryset = queryset.filter(listed=True)
        return super().filter_queryset(queryset)

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

    def filter_collection(self, qs, name, collection):
        if not collection.can_read(self.request):
            return qs.none()
        qs = qs.filter(collections=collection.id)
        qs = self.apply_data_filters(qs, collection.settings.get('filters', []))
        return qs

    def filter_portal(self, qs, name, portal):
        qs = qs.filter(portal=portal.id)
        qs = self.apply_data_filters(qs, portal.settings.get('filters', []))
        return qs

    def apply_data_filters(self, qs, filters):
        has_query = self.request.GET.get('q')

        for filt in filters:
            es_key = filt['key'].replace('__', '.')
            if has_query and filt.get('facet'):
                qs = qs.add_aggregation([es_key])

            if not filt['key'].startswith('data__'):
                continue
            val = self.request.GET.get(filt['key'])
            if not val:
                continue
            data_type = filt.get('datatype')
            if data_type:
                try:
                    if data_type == 'int':
                        val = int(val)
                except ValueError:
                    continue
            qs = qs.filter(**{es_key: val})
        return qs

    def filter_document(self, qs, name, value):
        if not value.can_read(self.request):
            return qs.none()
        return qs.filter(document=value.id)

    def filter_user(self, qs, name, value):
        return qs.filter(user=value.id)

    def filter_number(self, qs, name, value):
        return qs.filter(number=int(value))
