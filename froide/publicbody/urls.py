from django.urls import include, path, re_path
from django.utils.translation import pgettext_lazy
from django.views.generic.base import RedirectView

from .admin import pb_admin_site
from .views import (
    PublicBodyAcceptProposalView,
    PublicBodyChangeProposalView,
    PublicBodyProposalView,
    PublicBodySearch,
    PublicBodyView,
    publicbody_shortlink,
)

entities_url_patterns = [
    path(pgettext_lazy("url part", "admin/"), pb_admin_site.urls),
    path(
        pgettext_lazy("url part", "propose/"),
        PublicBodyProposalView.as_view(),
        name="publicbody-propose",
    ),
    path(
        pgettext_lazy("url part", "change/<int:pk>/"),
        PublicBodyChangeProposalView.as_view(),
        name="publicbody-change",
    ),
    path(
        pgettext_lazy("url part", "accept/<int:pk>/"),
        PublicBodyAcceptProposalView.as_view(),
        name="publicbody-accept",
    ),
    path("", PublicBodySearch.as_view(), name="publicbody-list"),
    # Translators: part in Public Body URL
    path(
        pgettext_lazy("url part", "topic/<slug:category>/"),
        PublicBodySearch.as_view(),
        name="publicbody-list",
    ),
    path("<slug:jurisdiction>/", PublicBodySearch.as_view(), name="publicbody-list"),
    # Translators: part in Public Body URL
    path(
        pgettext_lazy("url part", "<slug:jurisdiction>/topic/<slug:category>/"),
        PublicBodySearch.as_view(),
        name="publicbody-list",
    ),
]

urlpatterns = [
    re_path(
        pgettext_lazy("url part", r"^b/(?P<obj_id>\d+)/?$"),
        publicbody_shortlink,
        name="publicbody-publicbody_shortlink",
    ),
    path(
        pgettext_lazy("url part", "entity/<int:pk>/"),
        PublicBodyView.as_view(),
        name="publicbody-show",
    ),
    path(
        pgettext_lazy("url part", "entity/<int:pk>/<slug:slug>/"),
        PublicBodyView.as_view(),
        name="publicbody-show",
    ),
    path(
        pgettext_lazy("url part", "entity/<slug:slug>/"),
        PublicBodyView.as_view(),
        name="publicbody-show",
    ),
    path(
        pgettext_lazy("url part", "entity/"),
        RedirectView.as_view(pattern_name="publicbody-list", permanent=True),
    ),
    path(pgettext_lazy("url part", "entities/"), include(entities_url_patterns)),
]
