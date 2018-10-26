import functools
import re
from urllib.parse import urlencode

from django.shortcuts import render, redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView
from django.urls import reverse
from django.utils.functional import cached_property

from froide.helper.utils import render_403
from froide.helper.search import (
    SearchQuerySetWrapper, resolve_facet, make_filter_url,
    get_pagination_vars, ElasticsearchPaginator
)

from froide.publicbody.models import Jurisdiction

from ..models import FoiRequest, FoiAttachment
from ..feeds import LatestFoiRequestsFeed, LatestFoiRequestsFeedAtom
from ..filters import (
    get_filter_data, get_active_filters, FoiRequestFilterSet
)
from ..documents import FoiRequestDocument


NUM_RE = re.compile(r'^\[?\#?(\d+)\]?$')


class BaseListRequestView(ListView):
    allow_empty = True
    template_name = 'foirequest/list.html'
    paginate_by = 30
    paginator_class = ElasticsearchPaginator
    show_filters = {
        'jurisdiction', 'status', 'category'
    }
    advanced_filters = {
        'jurisdiction', 'category'
    }

    facet_config = {
        'jurisdiction': {
            'model': Jurisdiction,
            'getter': lambda x: x['object'].slug,
            'label_getter': lambda x: x['object'].name,
            'label': _('jurisdictions'),
        }
    }

    def get_base_search(self):
        return FoiRequestDocument.search().filter('term', public=True)

    def get_filterset(self, *args, **kwargs):
        return FoiRequestFilterSet(*args, **kwargs, view=self)

    @cached_property
    def has_advanced_filters(self):
        return bool(set(self.filtered_objs) & self.advanced_filters)

    def get_queryset(self):
        self.filter_data = get_filter_data(self.kwargs, dict(self.request.GET.items()))
        s = self.get_base_search()
        self.has_query = self.filter_data.get('q')
        if not self.has_query:
            s = s.sort('-last_message')
        else:
            # s = s.highlight_options(encoder='html')
            s = s.highlight('content')
            s = s.sort('_score', '-last_message')

        sqs = SearchQuerySetWrapper(s, FoiRequest)

        filtered = self.get_filterset(self.filter_data, queryset=sqs)
        self.form = filtered.form
        self.form.is_valid()

        # Set only valid data on widgets so they can render filter links
        data_clean_only = {
            k: v for k, v in self.filter_data.items()
            if k in self.form.cleaned_data
        }
        for name, field in filtered.form.fields.items():
            field.widget.data = data_clean_only

        sqs = filtered.qs

        sqs = self.add_facets(sqs)

        filtered_objs = filtered.form.cleaned_data
        self.filtered_objs = {k: v for k, v in filtered_objs.items() if v}

        return sqs

    def make_filter_url(self, data):
        return make_filter_url(
            self.request.resolver_match.url_name,
            data
        )

    def show_facets(self):
        return True

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
        queryset = sqs.wrap_queryset(sqs.to_queryset().select_related(
            'public_body',
            'jurisdiction'
        ))

        self.facets = None
        if queryset:
            self.facets = self.resolve_facets(sqs)

        return (paginator, page, queryset, is_paginated)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'page_title': _("FoI Requests"),
            'count': self.count,
            'form': self.form,
            'facets': self.facets,
            'facet_config': self.facet_config,
            'has_query': self.has_query,
            'show_filters': self.show_filters,
            'is_filtered': bool(set(self.filter_data) - {'q'}),
            'getvars': get_pagination_vars(self.filter_data),
            'filtered_objects': self.filtered_objs
        })
        return context


class ListRequestView(BaseListRequestView):
    feed = None

    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '')
        id_match = NUM_RE.match(q)
        if id_match is not None:
            try:
                req = FoiRequest.objects.get(pk=id_match.group(1))
                return redirect(req)
            except FoiRequest.DoesNotExist:
                pass
        return super().get(request, *args, **kwargs)

    def show_facets(self):
        return self.has_query

    def make_filter_url(self, data):
        return make_filter_url(
            self.request.resolver_match.url_name,
            data,
            get_active_filters=get_active_filters
        )

    def render_to_response(self, context, **response_kwargs):
        if self.feed is not None:
            if self.feed == 'rss':
                klass = LatestFoiRequestsFeed
            else:
                klass = LatestFoiRequestsFeedAtom
            feed_obj = klass(
                context['object_list'],
                data=self.filtered_objs,
                make_url=functools.partial(
                    make_filter_url,
                    data=self.filter_data,
                    get_active_filters=get_active_filters
                )
            )
            return feed_obj(self.request)

        return super().render_to_response(
            context, **response_kwargs
        )


def search(request):
    params = urlencode({'q': request.GET.get('q', '')})
    return redirect(reverse('foirequest-list') + '?' + params)


def list_unchecked(request):
    if not request.user.is_staff:
        return render_403(request)
    foirequests = FoiRequest.published.filter(checked=False).order_by('-id')[:30]
    attachments = FoiAttachment.objects.filter(is_redacted=False, redacted__isnull=True,
        approved=False, can_approve=True).order_by('-id')[:30]
    return render(request, 'foirequest/list_unchecked.html', {
        'foirequests': foirequests,
        'attachments': attachments
    })
