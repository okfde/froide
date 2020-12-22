from django.urls import path
from django.utils.translation import pgettext_lazy

from .views import (
    PublicBodySearch, PublicBodyProposalView, PublicBodyChangeProposalView,
    PublicBodyAcceptProposalView
)


urlpatterns = [
    path(pgettext_lazy('url part', "propose/"),
        PublicBodyProposalView.as_view(), name="publicbody-propose"),

    path(pgettext_lazy('url part', "change/<int:pk>/"),
        PublicBodyChangeProposalView.as_view(), name="publicbody-change"),

    path(pgettext_lazy('url part', "accept/<int:pk>/"),
        PublicBodyAcceptProposalView.as_view(), name="publicbody-accept"),

    path("", PublicBodySearch.as_view(), name="publicbody-list"),
    # Translators: part in Public Body URL
    path(pgettext_lazy('url part', "topic/<slug:category>/"),
            PublicBodySearch.as_view(), name="publicbody-list"),
    path("<slug:jurisdiction>/",
            PublicBodySearch.as_view(), name="publicbody-list"),
    # Translators: part in Public Body URL
    path(pgettext_lazy('url part', "<slug:jurisdiction>/topic/<slug:category>/"),
            PublicBodySearch.as_view(), name="publicbody-list"),
]
