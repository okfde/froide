from django_filters import rest_framework as filters
from elasticsearch_dsl.query import Q as ESQ

from froide.team.models import Team

from ..api_utils import ElasticLimitOffsetPagination
from . import SearchQuerySetWrapper


class ESQueryFilterBackend(filters.DjangoFilterBackend):
    def get_filterset_class(self, view, queryset=None):
        return view.searchfilterset_class


class ESQueryMixin:
    search_model = None
    search_document = None
    read_token_scopes = []
    searchfilter_backend = ESQueryFilterBackend()
    searchfilterset_class = None

    def search_view(self, request):
        self.sqs = self.get_searchqueryset()

        if self.searchfilterset_class is not None:
            self.sqs = self.searchfilter_backend.filter_queryset(
                self.request, self.sqs, self
            )

        has_query = request.GET.get("q")
        if has_query:
            self.sqs.sqs = self.sqs.sqs.highlight("content")
            self.sqs.sqs = self.sqs.sqs.sort("_score")

        paginator = ElasticLimitOffsetPagination()
        paginator.paginate_queryset(self.sqs, self.request, view=self)

        qs = self.optimize_query(self.sqs.to_queryset())
        self.queryset = self.sqs.wrap_queryset(qs)

        serializer = self.get_serializer(self.queryset, many=True)
        data = serializer.data

        return paginator.get_paginated_response(data)

    def get_searchqueryset(self):
        sqs = self.search_document.search()
        sqs = self.filter_authenticated(sqs)
        return SearchQuerySetWrapper(sqs, self.search_model)

    def get_public_q(self):
        return ESQ("term", public=True)

    def filter_authenticated(self, sqs):
        user = self.request.user
        token = self.request.auth
        if not user.is_authenticated:
            return sqs.filter(self.get_public_q())
        else:
            # Either not OAuth or OAuth and valid token
            if not token and user.is_superuser:
                # No filters for super users
                return sqs
            elif not token or token.is_valid(self.read_token_scopes):
                return sqs.filter(
                    "bool",
                    should=[
                        # Bool query in filter context
                        # at least one should clause is required to match.
                        self.get_public_q(),
                        ESQ("term", user=user.pk),
                        ESQ("terms", team=Team.objects.get_list_for_user(user)),
                    ],
                )
        return sqs.filter(self.get_public_q())

    def optimize_query(self, qs):
        return qs
