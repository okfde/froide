from django.http import Http404
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import ListView

from .facets import SearchManager
from .filters import BaseSearchFilterSet
from .paginator import ElasticsearchPaginator
from .queryset import SearchQuerySetWrapper


class BaseSearchView(ListView):
    allow_empty = True
    search_name = None
    template_name = "helper/search/search_base.html"
    paginate_by = 25
    paginator_class = ElasticsearchPaginator
    show_filters = {}
    advanced_filters = {}
    has_facets = False
    facet_config = {}
    model = None
    document = None
    filterset = BaseSearchFilterSet
    default_sort = "_score"
    filtered_objs = None
    select_related = ()
    prefetch_related = ()
    search_url_name = ""
    search_manager_kwargs = {}
    object_template = None

    def get_search_manager(self):
        get_data = dict(self.request.GET.items())
        get_data.pop(self.page_kwarg, None)
        return SearchManager(
            self.facet_config,
            self.kwargs,
            get_data,
            search_url_name=self.search_url_name,
            **self.search_manager_kwargs,
        )

    def get_base_search(self):
        return self.document.search()

    def get_filterset(self, *args, **kwargs):
        if self.filterset:
            return self.filterset(
                *args, **kwargs, view=self, facet_config=self.facet_config
            )
        return None

    @cached_property
    def has_advanced_filters(self):
        return bool(set(self.filtered_objs) & self.advanced_filters)

    def get_search(self):
        self.search_manager = self.get_search_manager()

        s = self.get_base_search()
        self.has_query = self.request.GET.get("q")
        if not self.has_query:
            s = s.sort(self.default_sort)
        else:
            # Retrieve 10 fragments of highlighted text, to be reduced to 5 later on.
            s = s.highlight_options(encoder="html", number_of_fragments=10).highlight(
                "content"
            )
            s = s.sort("_score")
        return s

    def get_queryset(self):
        s = self.get_search()
        sqs = SearchQuerySetWrapper(s, self.model)

        filtered = self.get_filterset(
            self.search_manager.filter_data,
            queryset=sqs,
        )
        self.form = None
        if filtered is not None:
            self.form = filtered.form
            if not self.form.is_valid():
                raise Http404

            # Set only valid data on widgets so they can render filter links
            data_clean_only = {
                k: v
                for k, v in self.search_manager.filter_data.items()
                if k in self.form.cleaned_data
            }
            for _n, field in filtered.form.fields.items():
                field.widget.data = data_clean_only

            sqs = filtered.qs

            filtered_objs = filtered.form.cleaned_data
            self.filtered_objs = {k: v for k, v in filtered_objs.items() if v}

        sqs = self.add_facets(sqs)

        return sqs

    def show_facets(self):
        return self.has_facets

    def add_facets(self, sqs):
        if self.show_facets():
            sqs = sqs.add_aggregation(list(self.facet_config.keys()))
        return sqs

    def paginate_queryset(self, sqs, page_size):
        """
        Paginate with SearchQuerySet, but return queryset
        """
        paginator, page, sqs, is_paginated = super().paginate_queryset(sqs, page_size)

        self.count = sqs.count()
        qs = sqs.to_queryset()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if self.prefetch_related:
            qs = qs.prefetch_related(*self.prefetch_related)

        queryset = sqs.wrap_queryset(qs)

        if queryset:
            self.facets = self.search_manager.get_facets(sqs.get_facet_data())
        else:
            # Empty facets
            self.facets = {k: {"buckets": []} for k in self.facet_config}

        return (paginator, page, queryset, is_paginated)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "count": self.count,
                "form": self.form,
                "facets": self.facets,
                "search_name": self.search_name,
                "search_url": reverse(self.search_url_name),
                "facet_config": self.facet_config,
                "has_facets": any(bool(self.facets[x]["buckets"]) for x in self.facets),
                "has_query": self.has_query,
                "object_template": self.object_template,
                "show_filters": self.show_filters,
                "is_filtered": bool(set(self.search_manager.filter_data) - {"q"}),
                "getvars": self.search_manager.get_pagination_vars(),
                "filtered_objects": self.filtered_objs,
            }
        )
        return context
