from django.conf.urls.defaults import patterns
from django.utils.translation import pgettext

from foirequest.models import FoiRequest
from foirequest.feeds import LatestFoiRequestsFeed, LatestFoiRequestsFeedAtom


urlpatterns = patterns("",
    (r'^%s/$' % pgettext('URL part', 'not-foi'), 'foirequest.views.list_requests_not_foi', {}, 'foirequest-list_not_foi'),
    (r'^unchecked/$', 'foirequest.views.list_unchecked', {}, 'foirequest-list_unchecked'),
    (r'^%s/feed/$' % pgettext('URL part', 'latest'), LatestFoiRequestsFeedAtom(), {}, 'foirequest-feed_latest_atom'),
    (r'^%s/rss/$' % pgettext('URL part', 'latest'), LatestFoiRequestsFeed(), {}, 'foirequest-feed_latest'),
    # Translators: part in /request/to/public-body-slug URL
    (r'^submit$', 'foirequest.views.submit_request', {}, 'foirequest-submit_request'),
    (r'^search/json$', 'foirequest.views.search_similar', {}, 'foirequest-search_similar'),
)


foirequest_urls = [
    (r'^$', 'foirequest.views.list_requests', {}, 'foirequest-list'),
    # Translators: part in request filter URL
    (r'^%s/(?P<topic>[-\w]+)/$' % pgettext('URL part', 'topic'), 'foirequest.views.list_requests', {}, 'foirequest-list'),
    # Translators: part in request filter URL
    (r'^%s/(?P<tag>[-\w]+)/$' % pgettext('URL part', 'tag'), 'foirequest.views.list_requests', {}, 'foirequest-list'),
] + [(r'^(?P<status>%s)/$' % urlpart, 'foirequest.views.list_requests', {}, 'foirequest-list') for urlpart, status in FoiRequest.STATUS_URLS]

urlpatterns += patterns("",
    *foirequest_urls
)

urlpatterns += patterns("",
    *[(r'^(?P<jurisdiction>[-\w]+)/%s' % r[0][1:], r[1], r[2], r[3]) for r in foirequest_urls]
)
