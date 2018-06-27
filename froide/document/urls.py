from django.conf.urls import url

from .views import DocumentView

urlpatterns = [
    # url(r'^$', MyRequestsView.as_view(), name='document-index'),
    url(r"^(?P<pk>\d)\-(?P<slug>[-\w]+)/$", DocumentView.as_view(), name="document-detail"),
]
