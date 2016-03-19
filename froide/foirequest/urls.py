from django.utils.six import text_type as str
from django.core.urlresolvers import reverse
from django.conf.urls import patterns
from django.utils.translation import pgettext
from django.shortcuts import redirect


from .models import FoiRequest


urlpatterns = patterns("froide.foirequest.views",
    (r'^%s/$' % pgettext('URL part', 'not-foi'), 'list_requests',
        {'not_foi': True}, 'foirequest-list_not_foi'),

    # Old feed URL
    (r'^%s/feed/$' % pgettext('URL part', 'latest'),
        lambda r: redirect(reverse('foirequest-list_feed_atom'), permanent=True),
        {}, 'foirequest-feed_latest_atom'),
    (r'^%s/rss/$' % pgettext('URL part', 'latest'),
        lambda r: redirect(reverse('foirequest-list_feed'), permanent=True),
        {}, 'foirequest-feed_latest'),

    (r'^unchecked/$', 'list_unchecked', {}, 'foirequest-list_unchecked'),
    # Translators: part in /request/to/public-body-slug URL
    (r'^submit$', 'submit_request', {}, 'foirequest-submit_request'),
)


foirequest_urls = [
    (r'^$', 'list_requests', {}, 'foirequest-list'),
    (r'^feed/$', 'list_requests',
        {'feed': 'atom'}, 'foirequest-list_feed_atom'),
    (r'^rss/$', 'list_requests',
        {'feed': 'rss'}, 'foirequest-list_feed'),
    (r'^u/(?P<user_id>\d+)/(?P<token>\w{32})/(?P<user_filter>(follow))/(?P<feed>(rss|atom))/$', 'list_requests', {}, 
        'foirequest-list_feed'),
    (r'^u/(?P<user_id>\d+)/(?P<token>\w{32})/(?P<feed>(rss|atom))/$','list_requests', {}, 
        'foirequest-list_feed'),

    # Translators: part in request filter URL
    (r'^%s/(?P<topic>[-\w]+)/$' % pgettext('URL part', 'topic'), 'list_requests', {},
        'foirequest-list'),
    (r'^%s/(?P<topic>[-\w]+)/feed/$' % pgettext('URL part', 'topic'), 'list_requests',
        {'feed': 'atom'}, 'foirequest-list_feed_atom'),
    (r'^%s/(?P<topic>[-\w]+)/rss/$' % pgettext('URL part', 'topic'), 'list_requests',
        {'feed': 'rss'}, 'foirequest-list_feed'),

    # Translators: part in request filter URL
    (r'^%s/(?P<tag>[-\w]+)/$' % pgettext('URL part', 'tag'), 'list_requests', {},
        'foirequest-list'),
    (r'^%s/(?P<tag>[-\w]+)/feed/$' % pgettext('URL part', 'tag'), 'list_requests',
        {'feed': 'atom'}, 'foirequest-list_feed_atom'),
    (r'^%s/(?P<tag>[-\w]+)/rss/$' % pgettext('URL part', 'tag'), 'list_requests',
        {'feed': 'rss'}, 'foirequest-list_feed'),

    # Translators: part in request filter URL
    (r'^%s/(?P<public_body>[-\w]+)/$' % pgettext('URL part', 'to'), 'list_requests', {},
        'foirequest-list'),
    (r'^%s/(?P<public_body>[-\w]+)/feed/$' % pgettext('URL part', 'to'), 'list_requests',
        {'feed': 'atom'}, 'foirequest-list_feed_atom'),
    (r'^%s/(?P<public_body>[-\w]+)/rss/$' % pgettext('URL part', 'to'), 'list_requests',
        {'feed': 'rss'}, 'foirequest-list_feed'),

] + [(r'^(?P<status>%s)/$' % str(urlinfo[0]), 'list_requests', {},
        'foirequest-list') for urlinfo in FoiRequest.get_status_url()
] + [(r'^(?P<status>%s)/feed/$' % str(urlinfo[0]), 'list_requests',
        {'feed': 'atom'},
        'foirequest-list_feed_atom') for urlinfo in FoiRequest.get_status_url()
] + [(r'^(?P<status>%s)/rss/$' % str(urlinfo[0]), 'list_requests',
        {'feed': 'rss'},
        'foirequest-list_feed') for urlinfo in FoiRequest.get_status_url()]

urlpatterns += patterns("froide.foirequest.views",
    *foirequest_urls
)

urlpatterns += patterns("froide.foirequest.views",
    *[(r'^(?P<jurisdiction>[-\w]+)/%s' % r[0][1:], r[1], r[2], r[3]) for r in foirequest_urls]
)
