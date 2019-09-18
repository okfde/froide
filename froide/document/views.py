from django import forms
from django.utils.translation import ugettext_lazy as _

from elasticsearch_dsl.query import Q
from taggit.models import Tag
import django_filters

from froide.helper.search.views import BaseSearchView
from froide.helper.search.filters import BaseSearchFilterSet

from filingcabinet.models import Page

from froide.publicbody.models import PublicBody, Jurisdiction
from froide.campaign.models import Campaign

from .documents import PageDocument


class DocumentFilterset(BaseSearchFilterSet):
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

    class Meta:
        model = Page
        fields = [
            'q', 'jurisdiction', 'campaign',
            'tag', 'publicbody',
        ]

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


class DocumentSearch(BaseSearchView):
    search_name = 'document'
    template_name = 'document/search.html'
    object_template = 'document/result_item.html'
    show_filters = {
        'jurisdiction', 'campaign',
    }
    advanced_filters = {
        'jurisdiction', 'campaign'
    }
    has_facets = True
    facet_config = {
        'tags': {
            'model': Tag,
            'getter': lambda x: x['object'].slug,
            'query_param': 'tag',
            'label_getter': lambda x: x['object'].name,
            'label': _('tags'),
        }
    }
    model = Page
    document = PageDocument
    filterset = DocumentFilterset
    search_url_name = 'document-search'
    select_related = ('document',)

    def get_base_search(self):
        # FIXME: add team
        q = Q('term', public=True)
        if self.request.user.is_authenticated:
            q |= Q('term', user=self.request.user.pk)
        return super().get_base_search().filter(q)
