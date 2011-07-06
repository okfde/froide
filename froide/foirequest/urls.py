from django.conf.urls.defaults import patterns
from django.utils.translation import pgettext

from foirequest.models import FoiRequest
from foirequest.feeds import LatestFoiRequestsFeed, LatestFoiRequestsFeedAtom


urlpatterns = patterns("",
    (r'^$', 'foirequest.views.list_requests', {}, 'foirequest-list'))

urlpatterns += patterns("",
    *[(r'^(?P<status>%s)/$' % urlpart, 'foirequest.views.list_requests',{}, 'foirequest-list') for urlpart, status in FoiRequest.STATUS_URLS])

urlpatterns += patterns("",
    (r'^%s/feed/$' % pgettext('URL part', 'latest'), LatestFoiRequestsFeedAtom(), {}, 'foirequest-feed_latest_atom'),
    (r'^%s/rss/$' % pgettext('URL part', 'latest'), LatestFoiRequestsFeed(), {}, 'foirequest-feed_latest'),
    # Translators: part in /request/to/public-body-slug URL
    (r'^submit$', 'foirequest.views.submit_request', {}, 'foirequest-submit_request'),
)
