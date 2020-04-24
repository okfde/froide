from django import forms
from django.utils.translation import gettext_lazy as _

import django_filters

from froide.helper.search.filters import BaseSearchFilterSet

from .models import PublicBody, Jurisdiction, Category, Classification


class PublicBodyFilterSet(BaseSearchFilterSet):
    query_fields = ['name^5', 'name_auto^3', 'content']

    q = django_filters.CharFilter(
        method='auto_query',
        widget=forms.TextInput(
            attrs={
                'placeholder': _('Search public bodies'),
                'class': 'form-control'
            }
        ),
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
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.get_category_list(),
        to_field_name='slug',
        empty_label=_('all categories'),
        widget=forms.Select(
            attrs={
                'label': _('category'),
                'class': 'form-control'
            }
        ),
        method='filter_category'
    )
    classification = django_filters.ModelChoiceFilter(
        queryset=Classification.objects.all(),
        to_field_name='slug',
        widget=forms.HiddenInput(),
        method='filter_classification'
    )

    class Meta:
        model = PublicBody
        fields = [
            'q', 'jurisdiction', 'category', 'classification'
        ]

    def filter_jurisdiction(self, qs, name, value):
        return qs.filter(jurisdiction=value.id)

    def filter_category(self, qs, name, value):
        return qs.filter(categories=value.id)

    def filter_classification(self, qs, name, value):
        return qs.filter(classification=value.id)
