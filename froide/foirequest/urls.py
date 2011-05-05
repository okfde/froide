from django.conf.urls.defaults import patterns, url
from django.utils.translation import pgettext

from foirequest.feeds import (LatestFoiRequestsFeed, 
    LatestFoiRequestsFeedAtom, FoiRequestFeed, FoiRequestFeedAtom)


urlpatterns = patterns("",
    (r'^$', 'foirequest.views.list_requests', {}, 'foirequest-list'),
    (r'^latest/feed/$', LatestFoiRequestsFeedAtom(), {}, 'foirequest-feed_latest_atom'),
    (r'^latest/rss/$', LatestFoiRequestsFeed(), {}, 'foirequest-feed_latest'),
    # Translators: part in /request/to/public-body-slug URL
    (r'^%s/(?P<public_body>[-\w]+)/$' % pgettext('URL part', 'to'), 'foirequest.views.make_request', {}, 'foirequest-make_request'),
    (r'^submit$', 'foirequest.views.submit_request', {}, 'foirequest-submit_request'),
    (r'^to/(?P<public_body>[-\w]+)/submit$', 'foirequest.views.submit_request', {}, 'foirequest-submit_request'),
    url(r"^(?P<slug>[-\w]+)/$", 'foirequest.views.show', name="foirequest-show"),
   url(r"^(?P<slug>[-\w]+)/feed/$", FoiRequestFeedAtom(), name="foirequest-feed_atom"),
    url(r"^(?P<slug>[-\w]+)/rss/$", FoiRequestFeed(), name="foirequest-feed"),
    url(r"^(?P<slug>[-\w]+)/suggest/public-body/$", 'foirequest.views.suggest_public_body', name="foirequest-suggest_public_body"),
    url(r"^(?P<slug>[-\w]+)/set/public-body/$", 'foirequest.views.set_public_body', name="foirequest-set_public_body"),
    url(r"^(?P<slug>[-\w]+)/set/status/$", 'foirequest.views.set_status', name="foirequest-set_status"),
    url(r"^(?P<slug>[-\w]+)/send/message/$", 'foirequest.views.send_message', name="foirequest-send_message"),

)
