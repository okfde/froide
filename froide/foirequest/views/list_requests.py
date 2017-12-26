from __future__ import unicode_literals

from django.utils.six import text_type as str

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext_lazy as _

from haystack.query import SearchQuerySet
from taggit.models import Tag

from froide.publicbody.models import PublicBody, Category, Jurisdiction
from froide.helper.utils import render_403

from ..models import FoiRequest, FoiAttachment
from ..feeds import LatestFoiRequestsFeed, LatestFoiRequestsFeedAtom


def list_requests(request, status=None, topic=None, tag=None,
        jurisdiction=None, public_body=None, not_foi=False, feed=None):
    context = {
        'filtered': True
    }
    manager = FoiRequest.published
    if not_foi:
        manager = FoiRequest.published_not_foi
    topic_list = Category.objects.get_category_list()
    if status is None:
        status = request.GET.get(str(_('status')), None)
    status_url = status
    foi_requests = manager.for_list_view()
    if status is not None:
        func_status = FoiRequest.get_status_from_url(status)
        if func_status is None:
            raise Http404
        func, status = func_status
        foi_requests = foi_requests.filter(func(status))
        context.update({
            'status': FoiRequest.get_readable_status(status),
            'status_description': FoiRequest.get_status_description(status)
        })
    elif topic is not None:
        topic = get_object_or_404(Category, slug=topic)
        foi_requests = manager.for_list_view().filter(public_body__categories=topic)
        context.update({
            'topic': topic,
        })
    elif tag is not None:
        tag = get_object_or_404(Tag, slug=tag)
        foi_requests = manager.for_list_view().filter(tags=tag)
        context.update({
            'tag': tag
        })
    else:
        foi_requests = manager.for_list_view()
        context['filtered'] = False

    if jurisdiction is not None:
        jurisdiction = get_object_or_404(Jurisdiction, slug=jurisdiction)
        foi_requests = foi_requests.filter(jurisdiction=jurisdiction)
        context.update({
            'jurisdiction': jurisdiction
        })
    elif public_body is not None:
        public_body = get_object_or_404(PublicBody, slug=public_body)
        foi_requests = foi_requests.filter(public_body=public_body)
        context.update({
            'public_body': public_body
        })
        context['filtered'] = True
        context['jurisdiction_list'] = Jurisdiction.objects.get_visible()
    else:
        context['jurisdiction_list'] = Jurisdiction.objects.get_visible()
        context['filtered'] = False

    if feed is not None:
        if feed == 'rss':
            klass = LatestFoiRequestsFeed
        else:
            klass = LatestFoiRequestsFeedAtom
        return klass(foi_requests, status=status_url, topic=topic,
            tag=tag, jurisdiction=jurisdiction)(request)

    count = foi_requests.count()

    page = request.GET.get('page')
    paginator = Paginator(foi_requests, 20)

    if request.GET.get('all') is not None:
        if count <= 500:
            paginator = Paginator(foi_requests, count)
    try:
        foi_requests = paginator.page(page)
    except PageNotAnInteger:
        foi_requests = paginator.page(1)
    except EmptyPage:
        foi_requests = paginator.page(paginator.num_pages)

    context.update({
        'page_title': _("FoI Requests"),
        'count': count,
        'not_foi': not_foi,
        'object_list': foi_requests,
        'status_list': [(str(x[0]),
            FoiRequest.get_readable_status(x[2]),
            x[2]) for x in FoiRequest.get_status_url()],
        'topic_list': topic_list
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
