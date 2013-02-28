from django.conf.urls import patterns
from django.utils.translation import pgettext


urlpatterns = patterns("froide.foirequest.views",
    # Translators: part in /request/to/public-body-slug URL
    (r'^$', 'make_request', {}, 'foirequest-make_request'),
    (r'^%s/(?P<public_body>[-\w]+)/$' % pgettext('URL part', 'to'), 'make_request', {},
        'foirequest-make_request'),
    (r'^%s/(?P<public_body>[-\w]+)/submit$' % pgettext('URL part', 'to'),
        'submit_request', {}, 'foirequest-submit_request'),
)
