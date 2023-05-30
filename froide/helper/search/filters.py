from django import forms
from django.utils.translation import gettext_lazy as _

import django_filters
from elasticsearch_dsl.query import Q


class BaseSearchFilterSet(django_filters.FilterSet):
    query_fields = ["content"]

    q = django_filters.CharFilter(
        method="auto_query",
        widget=forms.TextInput(
            attrs={"placeholder": _("Enter search term"), "class": "form-control"}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.facet_config = kwargs.pop("facet_config", {})
        self.view = kwargs.pop("view", None)
        super().__init__(*args, **kwargs)

    def apply_filter(self, qs, name, *args, **kwargs):
        if name in self.facet_config:
            return qs.post_filter(name, *args, **kwargs)
        return qs.filter(name, *args, **kwargs)

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
            return qs.set_query(
                Q(
                    "simple_query_string",
                    query=value,
                    fields=self.query_fields,
                    default_operator="and",
                    lenient=True,
                )
            )
        return qs
