from django.conf.urls import url
from django.utils.translation import pgettext

from .views import (
    index, PublicBodyProposalView
)


urlpatterns = [
    url(r"^%s/$" % pgettext('URL part', 'propose'),
        PublicBodyProposalView.as_view(), name="publicbody-propose"),

    url(r"^$", index, name="publicbody-list"),
    # Translators: part in Public Body URL
    url(r"^%s/(?P<category>[-\w]+)/$" % pgettext('URL part', 'topic'),
            index, name="publicbody-list"),
    url(r"^(?P<jurisdiction>[-\w]+)/$",
            index, name="publicbody-list"),
    # Translators: part in Public Body URL
    url(r"^(?P<jurisdiction>[-\w]+)/%s/(?P<category>[-\w]+)/$" % pgettext('URL part', 'topic'),
            index, name="publicbody-list"),
]
