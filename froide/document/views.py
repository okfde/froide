from django.views.generic import DetailView

from .models import Document


class DocumentView(DetailView):
    model = Document
    query_pk_and_slug = True

    def get_queryset(self):
        # import ipdb; ipdb.set_trace()
        qs = super(DocumentView, self).get_queryset()
        return qs.filter(public=True)
