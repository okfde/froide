from django.shortcuts import redirect
from django.views.generic import DetailView

from .models import Document


class DocumentView(DetailView):
    model = Document

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.slug and self.kwargs.get('slug') is None:
            return redirect(self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self):
        qs = super(DocumentView, self).get_queryset()
        return qs.filter(public=True)
