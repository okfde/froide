import functools
import re
from urllib.parse import urlencode

from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from froide.helper.search.facets import make_filter_url
from froide.helper.search.views import BaseSearchView
from froide.publicbody.models import Jurisdiction

from ..documents import FoiRequestDocument
from ..feeds import LatestFoiRequestsFeed, LatestFoiRequestsFeedAtom
from ..filters import FoiRequestFilterSet, get_active_filters, get_filter_data
from ..models import FoiRequest

NUM_RE = re.compile(r"^\[?\#?(\d+)\]?$")


class BaseListRequestView(BaseSearchView):
    search_name = "foirequest"
    template_name = "foirequest/list.html"
    show_filters = {"jurisdiction", "status", "category", "campaign", "sort"}
    advanced_filters = {"jurisdiction", "category", "campaign"}
    has_facets = True
    facet_config = {
        "jurisdiction": {
            "model": Jurisdiction,
            "getter": lambda x: x["object"].slug,
            "label_getter": lambda x: x["object"].name,
            "label": _("jurisdictions"),
        }
    }
    search_url_name = "foirequest-list"
    default_sort = "-last_message"
    select_related = ("public_body", "jurisdiction")
    model = FoiRequest
    document = FoiRequestDocument
    filterset = FoiRequestFilterSet

    def get_base_search(self):
        return super().get_base_search().filter("term", public=True)

    def get_filter_data(self, kwargs, get_dict):
        return get_filter_data(kwargs, get_dict)


class ListRequestView(BaseListRequestView):
    feed = None

    def get(self, request, *args, **kwargs):
        q = request.GET.get("q", "")
        id_match = NUM_RE.match(q)
        if id_match is not None:
            try:
                req = FoiRequest.objects.get(pk=id_match.group(1))
                return redirect(req.get_absolute_short_url())
            except FoiRequest.DoesNotExist:
                pass
        return super().get(request, *args, **kwargs)

    def show_facets(self):
        return self.has_query

    def make_filter_url(self, data):
        return make_filter_url(
            self.request.resolver_match.url_name,
            data,
            get_active_filters=get_active_filters,
        )

    def render_to_response(self, context, **response_kwargs):
        if self.feed is not None:
            if self.feed == "rss":
                klass = LatestFoiRequestsFeed
            else:
                klass = LatestFoiRequestsFeedAtom
            feed_obj = klass(
                context["object_list"],
                data=self.filtered_objs,
                make_url=functools.partial(
                    make_filter_url,
                    data=self.filter_data,
                    get_active_filters=get_active_filters,
                ),
            )
            return feed_obj(self.request)

        return super().render_to_response(context, **response_kwargs)


def search(request):
    params = urlencode({"q": request.GET.get("q", "")})
    return redirect(reverse("foirequest-list") + "?" + params)
