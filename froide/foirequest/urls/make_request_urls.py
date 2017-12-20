from django.conf.urls import url
from django.utils.translation import pgettext

from ..views import MakeRequestView, DraftRequestView


urlpatterns = [
    # Translators: part in /request/to/public-body-slug URL
    url(r'^$', MakeRequestView.as_view(), name='foirequest-make_request'),
    url(r'^%s/(?P<publicbody_ids>\d+(?:\+\d+)*)/$' % pgettext('URL part', 'to'),
            MakeRequestView.as_view(), name='foirequest-make_request'),
    url(r'^%s/(?P<publicbody_slug>[-\w]+)/$' % pgettext('URL part', 'to'),
            MakeRequestView.as_view(), name='foirequest-make_request'),
    url(r'^%s/(?P<pk>\d+)/' % pgettext('URL part', 'draft'), DraftRequestView.as_view(), name='foirequest-make_draftrequest'),
]
