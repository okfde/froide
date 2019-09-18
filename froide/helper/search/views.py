from django.views.generic import ListView
from django.urls import reverse
from django.utils.functional import cached_property

from .queryset import SearchQuerySetWrapper
from .facets import resolve_facet, make_filter_url
from .utils import get_pagination_vars
from .paginator import ElasticsearchPaginator
from .filters import BaseSearchFilterSet


class BaseSearchView(ListView):
    allow_empty = True
    search_name = None
    template_name = 'helper/search/search_base.html'
    paginate_by = 30
    paginator_class = ElasticsearchPaginator
    show_filters = {}
    advanced_filters = {}
    has_facets = False
    facet_config = {}
    model = None
    document = None
    filterset = BaseSearchFilterSet
    default_sort = '_score'
    filtered_objs = None
    select_related = ()
    search_url_name = ''
    object_template = None

    def get_base_search(self):
        return self.document.search()

    def get_filterset(self, *args, **kwargs):
        if self.filterset:
            return self.filterset(*args, **kwargs, view=self)
        return None

    def get_filter_data(self, kwargs, get_dict):
        return get_dict

    @cached_property
    def has_advanced_filters(self):
        return bool(set(self.filtered_objs) & self.advanced_filters)

    def get_search(self):
        self.filter_data = self.get_filter_data(self.kwargs, dict(self.request.GET.items()))

        s = self.get_base_search()
        self.has_query = self.request.GET.get('q')
        if not self.has_query:
            s = s.sort(self.default_sort)
        else:
            s = s.highlight('content')
            s = s.sort('_score')
        return s

    def get_queryset(self):
        s = self.get_search()
        sqs = SearchQuerySetWrapper(s, self.model)

        filtered = self.get_filterset(self.filter_data, queryset=sqs)
        self.form = None
        if filtered is not None:
            self.form = filtered.form
            try:
                self.form.is_valid()
            except Exception:
                pass

            # Set only valid data on widgets so they can render filter links
            data_clean_only = {
                k: v for k, v in self.filter_data.items()
                if k in self.form.cleaned_data
            }
            for _n, field in filtered.form.fields.items():
                field.widget.data = data_clean_only

            sqs = filtered.qs

            filtered_objs = filtered.form.cleaned_data
            self.filtered_objs = {k: v for k, v in filtered_objs.items() if v}

        sqs = self.add_facets(sqs)

        return sqs

    def make_filter_url(self, data):
        return make_filter_url(
            self.search_url_name,
            data
        )

    def show_facets(self):
        return self.has_facets

    def add_facets(self, sqs):
        if self.show_facets():
            sqs = sqs.add_aggregation(
                list(self.facet_config.keys())
            )
        return sqs

    def get_facet_resolvers(self):
        return {
            key: resolve_facet(
                self.filter_data,
                getter=config.get('getter'),
                model=config.get('model'),
                query_param=config.get('query_param', key),
                label_getter=config.get('label_getter'),
                make_url=self.make_filter_url
            ) for key, config in self.facet_config.items()
        }

    def resolve_facets(self, sqs):
        if self.show_facets():
            return sqs.get_facets(resolvers=self.get_facet_resolvers())
        return None

    def paginate_queryset(self, sqs, page_size):
        """
        Paginate with SearchQuerySet, but return queryset
        """
        paginator, page, sqs, is_paginated = super().paginate_queryset(sqs, page_size)

        self.count = sqs.count()
        qs = sqs.to_queryset()
        if self.select_related:
            qs = qs.select_related(*self.select_related)

        queryset = sqs.wrap_queryset(qs)

        if queryset:
            self.facets = self.resolve_facets(sqs)
        else:
            # Empty facets
            self.facets = {
                k: {'buckets': []} for k in self.facet_config
            }

        return (paginator, page, queryset, is_paginated)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'count': self.count,
            'form': self.form,
            'facets': self.facets,
            'search_name': self.search_name,
            'search_url': reverse(self.search_url_name),
            'facet_config': self.facet_config,
            'has_query': self.has_query,
            'object_template': self.object_template,
            'show_filters': self.show_filters,
            'is_filtered': bool(set(self.filter_data) - {'q'}),
            'getvars': get_pagination_vars(self.filter_data),
            'filtered_objects': self.filtered_objs
        })
        return context
