from __future__ import unicode_literals

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _

from haystack.query import SearchQuerySet

from froide.publicbody.models import PublicBody
from froide.helper.utils import render_403

from ..models import FoiRequest, FoiAttachment
from ..feeds import LatestFoiRequestsFeed, LatestFoiRequestsFeedAtom
from ..filters import get_filter_data, FoiRequestFilterSet


def list_requests(request, not_foi=False, feed=None, **filter_kwargs):
    context = {
        'filtered': True
    }
    manager = FoiRequest.published
    if not_foi:
        manager = FoiRequest.published_not_foi

    foi_requests = manager.for_list_view()

    data = get_filter_data(filter_kwargs, dict(request.GET.items()))
    filtered = FoiRequestFilterSet(data, queryset=foi_requests)
    form = filtered.form
    form.is_valid()

    # Set only valid data on widgets so they can render filter links
    data_clean_only = {k: v for k, v in data.items() if k in form.cleaned_data}
    for name, field in filtered.form.fields.items():
        field.widget.data = data_clean_only

    foi_requests = filtered.qs

    filtered_objs = filtered.form.cleaned_data
    filtered_objs = {k: v for k, v in filtered_objs.items() if v}

    if feed is not None:
        foi_requests = foi_requests[:50]
        if feed == 'rss':
            klass = LatestFoiRequestsFeed
        else:
            klass = LatestFoiRequestsFeedAtom
        return klass(foi_requests, **filtered_objs)(request)

    page = request.GET.get('page')
    paginator = Paginator(foi_requests, 30)

    try:
        foi_requests = paginator.page(page)
    except PageNotAnInteger:
        foi_requests = paginator.page(1)
    except EmptyPage:
        foi_requests = paginator.page(paginator.num_pages)

    context.update({
        'page_title': _("FoI Requests"),
        'count': paginator.count,
        'not_foi': not_foi,
        'object_list': foi_requests,
        'form': form,
        'filtered_objects': filtered_objs
    })

    return render(request, 'foirequest/list.html', context)


def search(request):
    query = request.GET.get("q", "")
    foirequests = []
    publicbodies = []
    if query:
        results = SearchQuerySet().models(FoiRequest).auto_query(query)[:25]
        for result in results:
            if result.object and result.object.in_search_index():
                foirequests.append(result.object)
        results = SearchQuerySet().models(PublicBody).auto_query(query)[:25]
        for result in results:
            publicbodies.append(result.object)
    context = {
        "foirequests": foirequests,
        "publicbodies": publicbodies,
        "query": query
    }
    return render(request, "search/search.html", context)


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
