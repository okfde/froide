from django.urls import path, re_path
from django.utils.translation import pgettext_lazy

from ..views import (
    MakeRequestView, DraftRequestView, RequestSentView
)


urlpatterns = [
    # Translators: part in /request/to/public-body-slug URL
    path('', MakeRequestView.as_view(), name='foirequest-make_request'),
    re_path(pgettext_lazy('url part', r'^to/(?P<publicbody_ids>\d+(?:\+\d+)*)/$'),
            MakeRequestView.as_view(), name='foirequest-make_request'),
    re_path(pgettext_lazy('url part', r'^to/(?P<publicbody_slug>[-\w]+)/$'),
            MakeRequestView.as_view(), name='foirequest-make_request'),
    re_path(pgettext_lazy('url part', r'^draft/(?P<pk>\d+)/'),
        DraftRequestView.as_view(), name='foirequest-make_draftrequest'),
    re_path(pgettext_lazy('url part', r'^sent/$'), RequestSentView.as_view(),
        name='foirequest-request_sent'),
]
