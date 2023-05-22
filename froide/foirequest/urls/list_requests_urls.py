import re

from django.urls import include, path, register_converter
from django.utils.translation import pgettext_lazy
from django.views.generic.base import RedirectView

from ..filters import FOIREQUEST_FILTERS
from ..views import (
    ListRequestView,
    UserRequestFeedView,
    claim_draft,
    delete_draft,
    user_calendar,
)

STATUS_URLS = [str(x[0]) for x in FOIREQUEST_FILTERS]


class StatusUrlPartConverter:
    regex = "|".join(re.escape(x) for x in STATUS_URLS)

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(StatusUrlPartConverter, "status")

urlpatterns = [
    # Old feed URL
    path(
        pgettext_lazy("url part", "latest/feed/"),
        RedirectView.as_view(pattern_name="foirequest-list_feed_atom", permanent=True),
        name="foirequest-feed_latest_atom",
    ),
    path(
        pgettext_lazy("url part", "latest/rss/"),
        RedirectView.as_view(pattern_name="foirequest-list_feed", permanent=True),
        name="foirequest-feed_latest",
    ),
    path("delete-draft/", delete_draft, name="foirequest-delete_draft"),
    path("claim/<uuid:token>/", claim_draft, name="foirequest-claim_draft"),
]

foirequest_urls = [
    path("", ListRequestView.as_view(), name="foirequest-list"),
    path(
        "feed/",
        ListRequestView.as_view(feed="atom"),
        name="foirequest-list_feed_atom",
    ),
    path("rss/", ListRequestView.as_view(feed="rss"), name="foirequest-list_feed"),
    # Translators: part in request filter URL
    path(
        pgettext_lazy("url part", "topic/<slug:category>/"),
        ListRequestView.as_view(),
        name="foirequest-list",
    ),
    path(
        pgettext_lazy("url part", "topic/<slug:category>/feed/"),
        ListRequestView.as_view(feed="atom"),
        name="foirequest-list_feed_atom",
    ),
    path(
        pgettext_lazy("url part", "topic/<slug:category>/rss/"),
        ListRequestView.as_view(feed="rss"),
        name="foirequest-list_feed",
    ),
    # # Translators: part in request filter URL
    path(
        pgettext_lazy("url part", "tag/<slug:tag>/"),
        ListRequestView.as_view(),
        name="foirequest-list",
    ),
    path(
        pgettext_lazy("url part", "tag/<slug:tag>/feed/"),
        ListRequestView.as_view(feed="atom"),
        name="foirequest-list_feed_atom",
    ),
    path(
        pgettext_lazy("url part", "tag/<slug:tag>/rss/"),
        ListRequestView.as_view(feed="rss"),
        name="foirequest-list_feed",
    ),
    # # Translators: part in request filter URL
    path(
        pgettext_lazy("url part", "to/<slug:publicbody>/"),
        ListRequestView.as_view(),
        name="foirequest-list",
    ),
    path(
        pgettext_lazy("url part", "to/<slug:publicbody>/feed/"),
        ListRequestView.as_view(feed="atom"),
        name="foirequest-list_feed_atom",
    ),
    path(
        pgettext_lazy("url part", "to/<slug:publicbody>/rss/"),
        ListRequestView.as_view(feed="rss"),
        name="foirequest-list_feed",
    ),
    path(
        pgettext_lazy("url part", "token/<slug:token>/feed/"),
        UserRequestFeedView.as_view(feed="atom"),
        name="foirequest-user_list_feed_atom",
    ),
    path(
        pgettext_lazy("url part", "token/<slug:token>/rss/"),
        UserRequestFeedView.as_view(feed="rss"),
        name="foirequest-user_list_feed",
    ),
    path(
        pgettext_lazy("url part", "token/<slug:token>/calendar/"),
        user_calendar,
        name="foirequest-user_ical_calendar",
    ),
    path(
        "<status:status>/",
        ListRequestView.as_view(),
        name="foirequest-list",
    ),
    path(
        "<status:status>/feed/",
        ListRequestView.as_view(feed="atom"),
        name="foirequest-list_feed_atom",
    ),
    path(
        "<status:status>/rss/",
        ListRequestView.as_view(feed="rss"),
        name="foirequest-list_feed",
    ),
]

urlpatterns += foirequest_urls

urlpatterns += [path("<slug:jurisdiction>/", include(foirequest_urls))]
