from django.conf.urls import url
from django.utils.translation import pgettext_lazy

from filingcabinet.urls import urlpatterns as fc_urlpatterns

from .views import DocumentSearch


urlpatterns = [
    url(pgettext_lazy('url part', r"^search/$"), DocumentSearch.as_view(), name='document-search'),
] + fc_urlpatterns
