from django import http
from django.views.generic import DetailView, ListView


class JSONResponseMixin(object):
    def render_to_json_response(self, context):
        "Returns a JSON response containing 'context' as payload"
        return self.get_json_response(self.convert_context_to_json(context))

    def get_json_response(self, content, **httpresponse_kwargs):
        "Construct an `HttpResponse` object."
        return http.HttpResponse(content,
                                 content_type='application/json',
                                 **httpresponse_kwargs)


class JSONResponseListView(ListView, JSONResponseMixin):
    def get_context_data(self, **kwargs):
        self.format = "html"
        if "format" in self.kwargs:
            self.format = self.kwargs['format']
        context = super(JSONResponseListView, self).get_context_data(**kwargs)
        return context

    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        return "[%s]" % ",".join([o.as_json() for o in context['object_list']])


class JSONResponseDetailView(DetailView, JSONResponseMixin):
    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        return context['object'].as_json()

    def get_context_data(self, **kwargs):
        self.format = "html"
        if "format" in self.kwargs:
            self.format = self.kwargs['format']
        context = super(JSONResponseDetailView, self).get_context_data(**kwargs)
        return context

    def render_to_response(self, context):
        if self.format == "json":
            return self.render_to_json_response(context)
        else:
            return super(DetailView, self).render_to_response(context)
