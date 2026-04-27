from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from froide.helper.search.queryset import SearchQuerySetWrapper
from froide.helper.utils import update_query_params
from froide.searchalert.configuration import AlertConfiguration, AlertEvent


class DocumentAlertConfiguration(AlertConfiguration):
    key = "document"
    title = _("Documents")

    @classmethod
    def search(
        cls, query, start_date, user=None, item_count=5, **kwargs
    ) -> list[AlertEvent]:
        from .documents import PageDocument
        from .filters import PageDocumentFilterset
        from .models import Document

        s = PageDocument.search().filter("term", public=True)
        s = s.highlight_options(encoder="html", number_of_fragments=10).highlight(
            "content"
        )
        s = s.sort("-created_at")
        sqs = SearchQuerySetWrapper(s, Document)

        request_factory = RequestFactory()
        request = request_factory.get("/")
        request.user = AnonymousUser()

        filtered = PageDocumentFilterset(
            {"q": query, "created_at_after": start_date.date().strftime("%Y-%m-%d")},
            queryset=sqs,
            request=request,
        )
        sqs = filtered.qs
        count = sqs.count()
        qs = sqs.to_queryset()
        qs = qs.select_related("document")
        qs = qs[:item_count]
        queryset = sqs.wrap_queryset(qs)

        return (
            count,
            [
                AlertEvent(
                    title=page.document.title,
                    url=settings.SITE_URL + page.get_absolute_url(),
                    content=page.query_highlight,
                )
                for page in queryset
            ],
        )

    @classmethod
    def get_search_link(cls, query, start_date) -> str:
        base_url = settings.SITE_URL + reverse("document-search")
        return update_query_params(
            base_url,
            {
                "q": query,
                "created_at_after": start_date.date().strftime("%Y-%m-%d"),
            },
        )
