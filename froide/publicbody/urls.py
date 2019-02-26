from django.conf.urls import url
from django.utils.translation import pgettext

from .views import (
    PublicBodySearch, PublicBodyProposalView
)


urlpatterns = [
    url(r"^%s/$" % pgettext('URL part', 'propose'),
        PublicBodyProposalView.as_view(), name="publicbody-propose"),

    url(r"^$", PublicBodySearch.as_view(), name="publicbody-list"),
    # Translators: part in Public Body URL
    url(r"^%s/(?P<category>[-\w]+)/$" % pgettext('URL part', 'topic'),
            PublicBodySearch.as_view(), name="publicbody-list"),
    url(r"^(?P<jurisdiction>[-\w]+)/$",
            PublicBodySearch.as_view(), name="publicbody-list"),
    # Translators: part in Public Body URL
    url(r"^(?P<jurisdiction>[-\w]+)/%s/(?P<category>[-\w]+)/$" % pgettext('URL part', 'topic'),
            PublicBodySearch.as_view(), name="publicbody-list"),
]
