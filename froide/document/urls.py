from django.conf.urls import url
from django.conf import settings
from django.utils.translation import pgettext_lazy

from filingcabinet.urls import urlpatterns as fc_urlpatterns

from .views import (
    DocumentSearchView,
    DocumentFileDetailView
)


urlpatterns = [
    url(pgettext_lazy('url part', r"^search/$"), DocumentSearchView.as_view(), name='document-search'),
] + fc_urlpatterns


MEDIA_PATH = settings.MEDIA_URL
# Split off domain and leading slash
if MEDIA_PATH.startswith('http'):
    MEDIA_PATH = MEDIA_PATH.split('/', 3)[-1]
else:
    MEDIA_PATH = MEDIA_PATH[1:]


document_media_urlpatterns = [
    url(r'^%s%s/(?P<u1>[a-z0-9]{2})/(?P<u2>[a-z0-9]{2})/(?P<u3>[a-z0-9]{2})/(?P<uuid>[a-z0-9]{32})/(?P<filename>.+)' % (
        MEDIA_PATH, settings.FILINGCABINET_MEDIA_PRIVATE_PREFIX
    ), DocumentFileDetailView.as_view(), name='filingcabinet-auth_document')
]
