from django.conf.urls import url
from django.utils.translation import pgettext_lazy

from ..views import (
    MakeRequestView, DraftRequestView, RequestSentView
)


urlpatterns = [
    # Translators: part in /request/to/public-body-slug URL
    url(r'^$', MakeRequestView.as_view(), name='foirequest-make_request'),
    url(pgettext_lazy('url part', r'^to/(?P<publicbody_ids>\d+(?:\+\d+)*)/$'),
            MakeRequestView.as_view(), name='foirequest-make_request'),
    url(pgettext_lazy('url part', r'^to/(?P<publicbody_slug>[-\w]+)/$'),
            MakeRequestView.as_view(), name='foirequest-make_request'),
    url(pgettext_lazy('url part', r'^draft/(?P<pk>\d+)/'),
        DraftRequestView.as_view(), name='foirequest-make_draftrequest'),
    url(pgettext_lazy('url part', r'^sent/$'), RequestSentView.as_view(),
        name='foirequest-request_sent'),
]
