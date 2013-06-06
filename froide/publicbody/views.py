from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.core import urlresolvers
from django.utils import simplejson as json
from django.utils.translation import ugettext as _, ungettext
from django.contrib import messages
from django.template import TemplateDoesNotExist

from haystack.query import SearchQuerySet

from froide.foirequest.models import FoiRequest
from froide.helper.json_view import JSONResponseDetailView
from froide.helper.utils import render_400, render_403
from froide.helper.cache import cache_anonymous_page

from .models import (PublicBody,
    PublicBodyTopic, FoiLaw, Jurisdiction)
from .csv_import import CSVImporter


def index(request):
    context = {"topics": PublicBodyTopic.objects.get_list()}
    return render(request, 'publicbody/list_topic.html', context)


@cache_anonymous_page(15 * 60)
def show_jurisdiction(request, slug):
    jurisdiction = get_object_or_404(Jurisdiction, slug=slug)
    context = {
        "object": jurisdiction,
        "pb_count": PublicBody.objects.filter(jurisdiction=jurisdiction).count(),
        "laws": FoiLaw.objects.filter(meta=False,
            jurisdiction=jurisdiction).order_by('priority'),
        "foirequests": FoiRequest.published.filter(jurisdiction=jurisdiction)[:5]
    }
    try:
        return render(request,
            'publicbody/jurisdiction/%s.html' % jurisdiction.slug, context)
    except TemplateDoesNotExist:
        return render(request,
            'publicbody/jurisdiction.html', context)


def show_pb_jurisdiction(request, slug):
    jurisdiction = get_object_or_404(Jurisdiction, slug=slug)
    context = {
        "object": jurisdiction,
        "publicbodies": PublicBody.objects.filter(jurisdiction=jurisdiction)
    }
    return render(request, 'publicbody/pb_jurisdiction.html', context)


def show_topic(request, topic):
    topic = get_object_or_404(PublicBodyTopic, slug=topic)
    context = {
        "topic": topic,
        "object_list": PublicBody.objects.get_list()
                    .select_related('jurisdiction')
                    .filter(topic=topic)
                    .order_by("jurisdiction__rank", "jurisdiction__name", "name")
    }
    return render(request, 'publicbody/show_topic.html', context)


def show_foilaw(request, slug):
    law = get_object_or_404(FoiLaw, slug=slug)
    context = {"object": law}
    return render(request, 'publicbody/show_foilaw.html', context)


class PublicBodyDetailView(JSONResponseDetailView):
    model = PublicBody
    template_name = "publicbody/show.html"

    def get_context_data(self, **kwargs):
        context = super(PublicBodyDetailView, self).get_context_data(**kwargs)
        if self.format == "html":
            context['foi_requests'] = FoiRequest.published.filter(public_body=context['object'])[:10]
        return context


def search_json(request):
    query = request.GET.get("q", "")
    jurisdiction = request.GET.get('jurisdiction', None)
    # query = " AND ".join(query.split())
    result = SearchQuerySet().models(PublicBody).auto_query(query)
    if jurisdiction is not None:
        result = result.filter(jurisdiction=result.query.clean(jurisdiction))
    result = [{"name": x.name, "jurisdiction": x.jurisdiction,
            "id": x.pk, "url": x.url, "score": x.score} for x in list(result)]

    return HttpResponse(json.dumps(result), content_type="application/json")


def autocomplete(request):
    query = request.GET.get('query', '')
    jurisdiction = request.GET.get('jurisdiction', None)
    result = SearchQuerySet().models(PublicBody)
    result = result.autocomplete(name_auto=query)
    if jurisdiction is not None:
        result = result.filter(jurisdiction=result.query.clean(jurisdiction))
    names = [u"%s (%s)" % (x.name, x.jurisdiction) for x in result]
    data = [{"name": x.name, "jurisdiction": x.jurisdiction,
            "id": x.pk, "url": x.url} for x in result]
    response = {"query": query,
        "suggestions": names,
        "data": data
    }
    return HttpResponse(json.dumps(response), content_type="application/json")


def confirm(request):
    if not request.user.is_authenticated():
        return render_403(request)
    if not request.user.is_staff and not request.user.is_superuser:
        return render_403(request)
    try:
        pb = get_object_or_404(PublicBody, pk=int(request.POST.get('public_body', '')))
    except ValueError:
        return render_400(request)
    result = pb.confirm()
    if result is None:
        messages.add_message(request, messages.ERROR,
            _('This request was already confirmed.'))
    else:
        messages.add_message(request, messages.ERROR,
                ungettext('%(count)d message was sent.',
                    '%(count)d messages were sent', result
                    ) % {"count": result})
    return HttpResponseRedirect(
        urlresolvers.reverse('admin:publicbody_publicbody_change',
            args=(pb.id,)))


def import_csv(request):
    if not request.user.is_authenticated():
        return render_403(request)
    if not request.user.is_staff and not request.user.is_superuser:
        return render_403(request)
    if not request.method == 'POST':
        return render_403(request)
    importer = CSVImporter()
    url = request.POST.get('url')
    try:
        if not url:
            raise ValueError(_('You need to provide a url.'))
        importer.import_from_url(url)
    except Exception as e:
        messages.add_message(request, messages.ERROR, str(e))
    else:
        messages.add_message(request, messages.SUCCESS,
            _('Public Bodies were imported.'))
    return HttpResponseRedirect(
        urlresolvers.reverse('admin:publicbody_publicbody_changelist'))
