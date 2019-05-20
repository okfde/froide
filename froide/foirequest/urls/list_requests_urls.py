from django.conf.urls import url, include
from django.urls import path
from django.utils.translation import pgettext_lazy
from django.views.generic.base import RedirectView

from ..views import (
    list_unchecked, delete_draft, claim_draft,
    ListRequestView, UserRequestFeedView,
    user_calendar
)
from ..filters import FOIREQUEST_FILTERS


STATUS_URLS = [str(x[0]) for x in FOIREQUEST_FILTERS]

urlpatterns = [
    # Old feed URL
    url(pgettext_lazy('url part', r'^latest/feed/$'),
        RedirectView.as_view(pattern_name='foirequest-list_feed_atom', permanent=True),
        name='foirequest-feed_latest_atom'),
    url(pgettext_lazy('url part', r'^latest/rss/$'),
        RedirectView.as_view(pattern_name='foirequest-list_feed', permanent=True),
        name='foirequest-feed_latest'),

    url(r'^unchecked/$', list_unchecked, name='foirequest-list_unchecked'),
    url(r'^delete-draft$', delete_draft, name='foirequest-delete_draft'),
    path('claim/<uuid:token>/', claim_draft, name='foirequest-claim_draft'),
]

foirequest_urls = [
    url(r'^$', ListRequestView.as_view(), name='foirequest-list'),
    url(r'^feed/$', ListRequestView.as_view(feed='atom'), name='foirequest-list_feed_atom'),
    url(r'^rss/$', ListRequestView.as_view(feed='rss'), name='foirequest-list_feed'),

    # Translators: part in request filter URL
    url(pgettext_lazy('url part', r'^topic/(?P<category>[-\w]+)/$'),
        ListRequestView.as_view(), name='foirequest-list'),
    url(pgettext_lazy('url part', r'^topic/(?P<category>[-\w]+)/feed/$'),
        ListRequestView.as_view(feed='atom'), name='foirequest-list_feed_atom'),
    url(pgettext_lazy('url part', r'^topic/(?P<category>[-\w]+)/rss/$'),
        ListRequestView.as_view(feed='rss'), name='foirequest-list_feed'),

    # # Translators: part in request filter URL
    url(pgettext_lazy('url part', r'^tag/(?P<tag>[-\w]+)/$'),
        ListRequestView.as_view(), name='foirequest-list'),
    url(pgettext_lazy('url part', r'^tag/(?P<tag>[-\w]+)/feed/$'),
        ListRequestView.as_view(feed='atom'), name='foirequest-list_feed_atom'),
    url(pgettext_lazy('url part', r'^tag/(?P<tag>[-\w]+)/rss/$'),
        ListRequestView.as_view(feed='rss'), name='foirequest-list_feed'),

    # # Translators: part in request filter URL
    url(pgettext_lazy('url part', r'^to/(?P<publicbody>[-\w]+)/$'),
        ListRequestView.as_view(), name='foirequest-list'),
    url(pgettext_lazy('url part', r'^to/(?P<publicbody>[-\w]+)/feed/$'),
        ListRequestView.as_view(feed='atom'), name='foirequest-list_feed_atom'),
    url(pgettext_lazy('url part', r'^to/(?P<publicbody>[-\w]+)/rss/$'),
        ListRequestView.as_view(feed='rss'), name='foirequest-list_feed'),

    url(pgettext_lazy('url part', r'^token/(?P<token>[-\w]+)/feed/$'),
        UserRequestFeedView.as_view(feed='atom'), name='foirequest-user_list_feed_atom'),
    url(pgettext_lazy('url part', r'^token/(?P<token>[-\w]+)/rss/$'),
        UserRequestFeedView.as_view(feed='rss'), name='foirequest-user_list_feed'),
    url(pgettext_lazy('url part', r'^token/(?P<token>[-\w]+)/calendar/$'),
        user_calendar, name='foirequest-user_ical_calendar'),

] + [url(r'^(?P<status>%s)/$' % status, ListRequestView.as_view(),
         name='foirequest-list')
        for status in STATUS_URLS
] + [url(r'^(?P<status>%s)/feed/$' % status,
         ListRequestView.as_view(feed='atom'), name='foirequest-list_feed_atom')
        for status in STATUS_URLS
] + [url(r'^(?P<status>%s)/rss/$' % status,
         ListRequestView.as_view(feed='rss'), name='foirequest-list_feed')
        for status in STATUS_URLS
]

urlpatterns += foirequest_urls

urlpatterns += [
    url(r'^(?P<jurisdiction>[-\w]+)/', include(foirequest_urls))
]
