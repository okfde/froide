from django.conf import settings
from django.urls import include, path, re_path
from django.utils.translation import pgettext_lazy

from filingcabinet.urls import fc_urlpatterns

from .views import (
    DocumentFileDetailView,
    DocumentSearchFeedView,
    DocumentSearchView,
    set_description,
    set_title,
    upload_documents,
)

urlpatterns = [
    path("", include((fc_urlpatterns, "filingcabinet"), namespace=None)),
    path(
        pgettext_lazy("url part", "search/"),
        DocumentSearchView.as_view(),
        name="document-search",
    ),
    path(
        pgettext_lazy("url part", "search/feed/"),
        DocumentSearchFeedView.as_view(),
        name="document-search_feed",
    ),
    path(
        pgettext_lazy("url part", "upload/"), upload_documents, name="document-upload"
    ),
    path(
        pgettext_lazy("url part", "<int:pk>/set_title"),
        set_title,
        name="document-set_title",
    ),
    path(
        pgettext_lazy("url part", "<int:pk>/set_description"),
        set_description,
        name="document-set_description",
    ),
]


MEDIA_PATH = settings.MEDIA_URL
# Split off domain and leading slash
if MEDIA_PATH.startswith("http"):
    MEDIA_PATH = MEDIA_PATH.split("/", 3)[-1]
else:
    MEDIA_PATH = MEDIA_PATH[1:]


document_media_urlpatterns = [
    re_path(
        r"^%s%s/(?P<u1>[a-z0-9]{2})/(?P<u2>[a-z0-9]{2})/(?P<u3>[a-z0-9]{2})/(?P<uuid>[a-z0-9]{32})/(?P<filename>.+)"
        % (MEDIA_PATH, settings.FILINGCABINET_MEDIA_PRIVATE_PREFIX),
        DocumentFileDetailView.as_view(),
        name="filingcabinet-auth_document",
    )
]
