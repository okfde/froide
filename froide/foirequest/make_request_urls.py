from django.conf.urls import url
from django.utils.translation import pgettext

from .views import make_request


urlpatterns = [
    # Translators: part in /request/to/public-body-slug URL
    url(r'^$', make_request, name='foirequest-make_request'),
    url(r'^%s/(?P<publicbody_ids>\d+(?:\+\d+)*)/$' % pgettext('URL part', 'to'),
            make_request, name='foirequest-make_request'),
    url(r'^%s/(?P<publicbody_slug>[-\w]+)/$' % pgettext('URL part', 'to'),
            make_request, name='foirequest-make_request'),
]
