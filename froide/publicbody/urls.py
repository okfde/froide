from django.conf.urls.defaults import patterns, url
from publicbody.views import PublicBodyDetailView

urlpatterns = patterns("",
    url(r"^autocomplete/$", "publicbody.views.autocomplete", name="publicbody-autocomplete"),
    url(r"^search/$", "publicbody.views.search", name="publicbody-search"),    url(r"^(?P<pk>[\d+]).(?P<format>json)$", PublicBodyDetailView.as_view(), name="publicbody-show-json"),
    url(r"^(?P<slug>[-\w]+)$", PublicBodyDetailView.as_view(), name="publicbody-show"),
    url(r"^(?P<pk>\d+).(?P<format>json)$", PublicBodyDetailView.as_view(), name="publicbody-show-json"),
    url(r"^(?P<slug>[-\w]+).(?P<format>json)$", PublicBodyDetailView.as_view(), name="publicbody-show-json"),
)
