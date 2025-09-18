from django import forms
from django.utils.translation import gettext_lazy as _

import django_filters
from elasticsearch_dsl.query import Q

from froide.helper.search import get_query_preprocessor


class BaseSearchFilterSet(django_filters.FilterSet):
    query_fields = ["content"]

    q = django_filters.CharFilter(
        method="auto_query",
        widget=forms.TextInput(
            attrs={"placeholder": _("Enter search term"), "class": "form-control"}
        ),
        label=_("Search Term"),
    )

    def __init__(self, *args, **kwargs):
        self.facet_config = kwargs.pop("facet_config", {})
        self.view = kwargs.pop("view", None)
        self.query_preprocessor = get_query_preprocessor()
        super().__init__(*args, **kwargs)

    def apply_filter(self, qs, name, *args, **kwargs):
        if name in self.facet_config:
            return qs.post_filter(name, *args, **kwargs)
        return qs.filter(*args, **kwargs)

    def filter_queryset(self, queryset):
        """
        Filter the queryset with the underlying form's `cleaned_data`. You must
        call `is_valid()` or `errors` before calling this method.
        This method should be overridden if additional filtering needs to be
        applied to the queryset before it is cached.
        """
        for name, value in self.form.cleaned_data.items():
            queryset = self.filters[name].filter(queryset, value)
            # assert isinstance(queryset, models.QuerySet), \
            #     "Expected '%s.%s' to return a QuerySet, but got a %s instead." \
            #     % (type(self).__name__, name, type(queryset).__name__)
        return queryset

    def auto_query(self, qs, name, value):
        if value:
            query = self.query_preprocessor.prepare_query(value)
            return qs.set_query(
                Q(
                    "simple_query_string",
                    query=query,
                    fields=self.query_fields,
                    default_operator="and",
                    lenient=True,
                )
            )
        return qs


class BaseQueryPreprocessor:
    """
    Base class that can be overridden for custom search query preprocessing.
    """

    def prepare_query(self, text: str):
        """
        Preprocess the given search query text and return the processed text.

        This method can be overridden in subclasses to implement custom
        preprocessing logic.
        """
        return text
