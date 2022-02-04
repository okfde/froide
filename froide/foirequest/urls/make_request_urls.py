from django.urls import path, re_path
from django.utils.translation import pgettext_lazy

from ..views import DraftRequestView, MakeRequestView, RequestSentView

urlpatterns = [
    # Translators: part in /request/to/public-body-slug URL
    path("", MakeRequestView.as_view(), name="foirequest-make_request"),
    re_path(
        pgettext_lazy("url part", r"^to/(?P<publicbody_ids>\d+(?:\+\d+)*)/$"),
        MakeRequestView.as_view(),
        name="foirequest-make_request",
    ),
    path(
        pgettext_lazy("url part", "to/<slug:publicbody_slug>/"),
        MakeRequestView.as_view(),
        name="foirequest-make_request",
    ),
    path(
        pgettext_lazy("url part", "draft/<int:pk>/"),
        DraftRequestView.as_view(),
        name="foirequest-make_draftrequest",
    ),
    path(
        pgettext_lazy("url part", "sent/"),
        RequestSentView.as_view(),
        name="foirequest-request_sent",
    ),
]
