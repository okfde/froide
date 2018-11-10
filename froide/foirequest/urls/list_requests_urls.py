from django.conf.urls import url, include
from django.utils.translation import pgettext
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
    url(r'^%s/feed/$' % pgettext('URL part', 'latest'),
        RedirectView.as_view(pattern_name='foirequest-list_feed_atom', permanent=True),
        name='foirequest-feed_latest_atom'),
    url(r'^%s/rss/$' % pgettext('URL part', 'latest'),
        RedirectView.as_view(pattern_name='foirequest-list_feed', permanent=True),
        name='foirequest-feed_latest'),

    url(r'^unchecked/$', list_unchecked, name='foirequest-list_unchecked'),
    url(r'^delete-draft$', delete_draft, name='foirequest-delete_draft'),
    url(r'^claim/(?P<token>[^/]+)/$', claim_draft, name='foirequest-claim_draft'),
]

foirequest_urls = [
    url(r'^$', ListRequestView.as_view(), name='foirequest-list'),
    url(r'^feed/$', ListRequestView.as_view(feed='atom'), name='foirequest-list_feed_atom'),
    url(r'^rss/$', ListRequestView.as_view(feed='rss'), name='foirequest-list_feed'),

    # Translators: part in request filter URL
    url(r'^%s/(?P<category>[-\w]+)/$' % pgettext('URL part', 'topic'),
        ListRequestView.as_view(), name='foirequest-list'),
    url(r'^%s/(?P<category>[-\w]+)/feed/$' % pgettext('URL part', 'topic'),
        ListRequestView.as_view(feed='atom'), name='foirequest-list_feed_atom'),
    url(r'^%s/(?P<category>[-\w]+)/rss/$' % pgettext('URL part', 'topic'),
        ListRequestView.as_view(feed='rss'), name='foirequest-list_feed'),

    # # Translators: part in request filter URL
    url(r'^%s/(?P<tag>[-\w]+)/$' % pgettext('URL part', 'tag'),
        ListRequestView.as_view(), name='foirequest-list'),
    url(r'^%s/(?P<tag>[-\w]+)/feed/$' % pgettext('URL part', 'tag'),
        ListRequestView.as_view(feed='atom'), name='foirequest-list_feed_atom'),
    url(r'^%s/(?P<tag>[-\w]+)/rss/$' % pgettext('URL part', 'tag'),
        ListRequestView.as_view(feed='rss'), name='foirequest-list_feed'),

    # # Translators: part in request filter URL
    url(r'^%s/(?P<publicbody>[-\w]+)/$' % pgettext('URL part', 'to'),
        ListRequestView.as_view(), name='foirequest-list'),
    url(r'^%s/(?P<publicbody>[-\w]+)/feed/$' % pgettext('URL part', 'to'),
        ListRequestView.as_view(feed='atom'), name='foirequest-list_feed_atom'),
    url(r'^%s/(?P<publicbody>[-\w]+)/rss/$' % pgettext('URL part', 'to'),
        ListRequestView.as_view(feed='rss'), name='foirequest-list_feed'),

    url(r'^%s/(?P<token>[-\w]+)/feed/$' % pgettext('URL part', 'token'),
        UserRequestFeedView.as_view(feed='atom'), name='foirequest-user_list_feed_atom'),
    url(r'^%s/(?P<token>[-\w]+)/rss/$' % pgettext('URL part', 'token'),
        UserRequestFeedView.as_view(feed='rss'), name='foirequest-user_list_feed'),
    url(r'^%s/(?P<token>[-\w]+)/calendar/$' % pgettext('URL part', 'token'),
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
