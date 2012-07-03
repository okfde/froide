from django.conf.urls.defaults import patterns
from django.utils.translation import pgettext

from .models import FoiRequest
from .feeds import LatestFoiRequestsFeed, LatestFoiRequestsFeedAtom


urlpatterns = patterns("froide.foirequest.views",
    (r'^%s/$' % pgettext('URL part', 'not-foi'), 'list_requests_not_foi', {}, 'foirequest-list_not_foi'),
    (r'^unchecked/$', 'list_unchecked', {}, 'foirequest-list_unchecked'),
    (r'^%s/feed/$' % pgettext('URL part', 'latest'), LatestFoiRequestsFeedAtom(), {}, 'foirequest-feed_latest_atom'),
    (r'^%s/rss/$' % pgettext('URL part', 'latest'), LatestFoiRequestsFeed(), {}, 'foirequest-feed_latest'),
    # Translators: part in /request/to/public-body-slug URL
    (r'^submit$', 'submit_request', {}, 'foirequest-submit_request'),
    (r'^search/json$', 'search_similar', {}, 'foirequest-search_similar'),
)


foirequest_urls = [
    (r'^$', 'list_requests', {}, 'foirequest-list'),
    # Translators: part in request filter URL
    (r'^%s/(?P<topic>[-\w]+)/$' % pgettext('URL part', 'topic'), 'list_requests', {},
        'foirequest-list'),
    # Translators: part in request filter URL
    (r'^%s/(?P<tag>[-\w]+)/$' % pgettext('URL part', 'tag'), 'list_requests', {},
        'foirequest-list'),
] + [(r'^(?P<status>%s)/$' % urlpart, 'list_requests', {}, 'foirequest-list') for urlpart, status in FoiRequest.STATUS_URLS]

urlpatterns += patterns("froide.foirequest.views",
    *foirequest_urls
)

urlpatterns += patterns("froide.foirequest.views",
    *[(r'^(?P<jurisdiction>[-\w]+)/%s' % r[0][1:], r[1], r[2], r[3]) for r in foirequest_urls]
)
