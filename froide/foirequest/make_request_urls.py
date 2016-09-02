from django.conf.urls import url
from django.utils.translation import pgettext

from .views import make_request, submit_request


urlpatterns = [
    # Translators: part in /request/to/public-body-slug URL
    url(r'^$', make_request, name='foirequest-make_request'),
    url(r'^%s/(?P<public_body_id>\d+)/$' % pgettext('URL part', 'to'),
            make_request, name='foirequest-make_request'),
    url(r'^%s/(?P<public_body>[-\w]+)/$' % pgettext('URL part', 'to'),
            make_request, name='foirequest-make_request'),
    url(r'^%s/(?P<public_body>[-\w]+)/submit$' % pgettext('URL part', 'to'),
            submit_request, name='foirequest-submit_request'),
]
