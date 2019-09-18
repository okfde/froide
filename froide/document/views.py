from elasticsearch_dsl.query import Q

from froide.helper.search.views import BaseSearchView
from froide.helper.search.filters import BaseSearchFilterSet

from filingcabinet.models import Page

from .documents import PageDocument


class DocumentFilterset(BaseSearchFilterSet):
    query_fields = ['title^3', 'description^2', 'content']


class DocumentSearch(BaseSearchView):
    search_name = 'document'
    template_name = 'document/search.html'
    object_template = 'document/result_item.html'
    model = Page
    document = PageDocument
    filterset = DocumentFilterset
    search_url_name = 'document-search'
    select_related = ('document',)

    def get_base_search(self):
        # FIXME: add team
        q = Q('term', public=True)
        if self.request.user.is_authenticated:
            q |= Q('term', user=self.request.user.pk)
        return super().get_base_search().filter(q)
