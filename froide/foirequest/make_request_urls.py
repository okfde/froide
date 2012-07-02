from django.conf.urls.defaults import patterns
from django.utils.translation import pgettext


urlpatterns = patterns("",
    # Translators: part in /request/to/public-body-slug URL
    (r'^$', 'foirequest.views.make_request', {}, 'foirequest-make_request'),
    (r'^%s/(?P<public_body>[-\w]+)/$' % pgettext('URL part', 'to'), 'foirequest.views.make_request', {}, 'foirequest-make_request'),
    (r'^%s/(?P<public_body>[-\w]+)/submit$' % pgettext('URL part', 'to'), 'foirequest.views.submit_request', {}, 'foirequest-submit_request'),
)
