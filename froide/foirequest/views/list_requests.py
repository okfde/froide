from django.shortcuts import render, redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView
from django.urls import reverse

from froide.helper.utils import render_403
from froide.helper.search import (
    SearchQuerySetWrapper, resolve_facet, make_filter_url,
    get_pagination_vars
)

from froide.publicbody.models import Jurisdiction

from ..models import FoiRequest, FoiAttachment
from ..feeds import LatestFoiRequestsFeed, LatestFoiRequestsFeedAtom
from ..filters import (
    get_filter_data, get_active_filters, FoiRequestFilterSet
)
from ..documents import FoiRequestDocument


def make_url(data):
    return make_filter_url(
        'foirequest-list',
        data,
        get_active_filters=get_active_filters
    )


class ListRequestView(ListView):
    allow_empty = True
    template_name = 'foirequest/list.html'
    paginate_by = 30
    feed = None

    def get_queryset(self):
        self.filter_data = get_filter_data(self.kwargs, dict(self.request.GET.items()))
        s = FoiRequestDocument.search().filter('term', public=True)

        self.has_query = self.filter_data.get('q')
        if not self.has_query:
            s = s.sort('-last_message')
        else:
            s = s.sort('_score', '-last_message')

        sqs = SearchQuerySetWrapper(s, FoiRequest)

        filtered = FoiRequestFilterSet(self.filter_data, queryset=sqs)
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

        if self.has_query:
            sqs = sqs.add_aggregation([
                'jurisdiction'
            ])

        filtered_objs = filtered.form.cleaned_data
        self.filtered_objs = {k: v for k, v in filtered_objs.items() if v}

        return sqs

    def paginate_queryset(self, sqs, page_size):
        """
        Paginate with SearchQuerySet, but return queryset
        """
        paginator, page, sqs, is_paginated = super().paginate_queryset(sqs, page_size)

        self.count = sqs.count()
        queryset = sqs.to_queryset().select_related(
            'public_body',
            'jurisdiction'
        )
        self.facets = None
        if self.has_query:
            self.facets = sqs.get_facets(resolvers={
                'jurisdiction': resolve_facet(
                    self.filter_data,
                    lambda o: o.slug,
                    Jurisdiction,
                    make_url=make_url
                )
            })

        return (paginator, page, queryset, is_paginated)

    def get_context_data(self, **kwargs):
        context = super(ListRequestView, self).get_context_data(**kwargs)

        context.update({
            'page_title': _("FoI Requests"),
            'count': self.count,
            'form': self.form,
            'facets': self.facets,
            'has_query': self.has_query,
            'getvars': get_pagination_vars(self.filter_data),
            'filtered_objects': self.filtered_objs
        })
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.feed is not None:
            if self.feed == 'rss':
                klass = LatestFoiRequestsFeed
            else:
                klass = LatestFoiRequestsFeedAtom
            feed_obj = klass(context['object_list'], **self.filtered_objs)
            return feed_obj(self.request)

        return super(ListRequestView, self).render_to_response(
            context, **response_kwargs
        )


def search(request):
    return redirect(reverse('foirequest-list') + '?q=' + request.GET.get("q", ""))


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
