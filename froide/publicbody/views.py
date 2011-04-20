import json

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from haystack.query import SearchQuerySet, SQ

from publicbody.models import PublicBody
from froide.helper.json_view import JSONResponseDetailView


class PublicBodyDetailView(JSONResponseDetailView):
    model = PublicBody
    template_name = "publicbody/show.html"

    def get_context_data(self, **kwargs):
        context = super(JSONResponseDetailView, self).get_context_data(**kwargs)
        self.format = "html"
        if "format" in self.kwargs:
            self.format = self.kwargs['format']
        if self.format == "html":
            context['foi_requests'] = [] #FIXME: PublicBody.foirequest_set.latest()
        return context

def search(request):
    query = request.GET.get("q","")
    # query = " OR ".join(query.split())
    result = SearchQuerySet().models(PublicBody).auto_query(query)
    result = [{"name": x.name, "id": x.pk, "url": x.url} for x in result]
    return HttpResponse(json.dumps(result), content_type="application/json")

def autocomplete(request):
    result = SearchQuerySet().filter(
        SQ(name_auto=request.GET.get('q', '')) |
        SQ(topic_auto=request.GET.get('q', ''))
    ) 
    for x in result:
        print x.get_stored_fields()
    l = [x.get_stored_fields()['name'] for x in result]
    # l.extend([x.get_stored_fields()['name_auto'] for x in result])
    return HttpResponse(json.dumps(list(set(l))), content_type="application/json")

