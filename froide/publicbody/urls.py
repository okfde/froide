from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext as _

from publicbody.views import PublicBodyDetailView, PublicBodyListView

urlpatterns = patterns("",
    url(r"^$", PublicBodyListView.as_view(), name="publicbody-list"),
    url(r"^autocomplete/$", "publicbody.views.autocomplete", name="publicbody-autocomplete"),
    # Translators: part in Public Body URL
    url(r"^%s/$" % _('search'), "publicbody.views.search", name="publicbody-search"),
    url(r"^(?P<pk>[\d+]).(?P<format>json)$", PublicBodyDetailView.as_view(), name="publicbody-show-json"),
    url(r"^(?P<slug>[-\w]+)$", PublicBodyDetailView.as_view(), name="publicbody-show"),
    url(r"^(?P<pk>\d+).(?P<format>json)$", PublicBodyDetailView.as_view(), name="publicbody-show_json"),
    url(r"^(?P<slug>[-\w]+).(?P<format>json)$", PublicBodyDetailView.as_view(), name="publicbody-show_json"),
    url(r"^confirm/$", 'publicbody.views.confirm', name="publicbody-confirm"),
)
