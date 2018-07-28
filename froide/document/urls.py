# from django.conf.urls import url

# from .views import DocumentView

from filingcabinet.urls import urlpatterns as fc_urlpatterns

urlpatterns = [
    # url(r'^$', MyRequestsView.as_view(), name='document-index'),
    # url(r"^(?P<pk>\d+)\-(?P<slug>[-\w]+)/$", DocumentView.as_view(), name="document-detail"),
    # url(r"^(?P<pk>\d+)/$", DocumentView.as_view(), name="document-detail_short"),
] + fc_urlpatterns
