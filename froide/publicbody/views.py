import json

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.core import urlresolvers
from django.utils.translation import ugettext as _, ungettext
from django.contrib import messages

from haystack.query import SearchQuerySet

from publicbody.models import PublicBody, PublicBodyTopic, FoiLaw
from froide.helper.json_view import (JSONResponseDetailView,
        JSONResponseListView)
from froide.helper.utils import render_400, render_403


class PublicBodyListView(JSONResponseListView):
    model = PublicBody
    template_name = "publicbody/list.html"

    def get_context_data(self, **kwargs):
        context = super(PublicBodyListView, self).get_context_data(**kwargs)
        return context

def index(request):
    context = {"topics": PublicBodyTopic.objects.order_by("name")}
    return render(request, 'publicbody/list_topic.html', context)

def show_topic(request, topic):
    topic = get_object_or_404(PublicBodyTopic, slug=topic)
    context = {"topic": topic, 
            "object_list": PublicBody.objects.filter(topic=topic).order_by("name")}
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
            context['foi_requests'] = context['object'].foirequest_set.order_by('last_message')[:10]
        return context

def search(request):
    query = request.GET.get("q", "")
    # query = " AND ".join(query.split())
    result = list(SearchQuerySet().models(PublicBody).auto_query(query))
    result = [{"name": x.name, "id": x.pk, "url": x.url, "score": x.score} for x in result]
    
    return HttpResponse(json.dumps(result), content_type="application/json")

def autocomplete(request):
    query = request.GET.get('query', '')
    result = SearchQuerySet().autocomplete(name_auto=query)
    names = [x.name for x in result]
    data = [{"name": x.name, "id": x.pk, "url": x.url} for x in result]
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
