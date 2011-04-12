from django import http
from django.views.generic import DetailView

class JSONResponseDetailView(DetailView):
    def render_to_json_response(self, context):
        "Returns a JSON response containing 'context' as payload"
        return self.get_json_response(self.convert_context_to_json(context))

    def get_json_response(self, content, **httpresponse_kwargs):
        "Construct an `HttpResponse` object."
        return http.HttpResponse(content,
                                 content_type='application/json',
                                 **httpresponse_kwargs)

    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        return context['object'].as_json()

    def render_to_response(self, context):
        if self.format == "json":
            return self.render_to_json_response(context)
        else:
            return super(DetailView, self).render_to_response(context)


