from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext as _

from haystack.query import SearchQuerySet
from haystack.views import SearchView, search_view_factory

from publicbody.models import PublicBody
from publicbody.views import PublicBodyDetailView
from publicbody.forms import TopicSearchForm


# Without threading...
urlpatterns = patterns('haystack.views',
    url(r'^%s/$' % _('search'), search_view_factory(
        view_class=SearchView,
        template='publicbody/search.html',
        searchqueryset=SearchQuerySet().models(PublicBody),
        form_class=TopicSearchForm
    ), name='publicbody-search'),
)

urlpatterns += patterns("",
    url(r"^$", 'publicbody.views.index', name="publicbody-list"),
    url(r"^autocomplete/$", "publicbody.views.autocomplete", name="publicbody-autocomplete"),
    # Translators: part in Public Body URL
    url(r"^%s/json/$" % _('search'), "publicbody.views.search_json", name="publicbody-search_json"),
    url(r"^%s/(?P<topic>[-\w]+)$" % _('topic'), 'publicbody.views.show_topic', name="publicbody-show_topic"),
    url(r"^(?P<pk>[\d+]).(?P<format>json)$", PublicBodyDetailView.as_view(), name="publicbody-show-json"),
    url(r"^(?P<slug>[-\w]+)$", PublicBodyDetailView.as_view(), name="publicbody-show"),
    url(r"^(?P<pk>\d+).(?P<format>json)$", PublicBodyDetailView.as_view(), name="publicbody-show_json"),
    url(r"^(?P<slug>[-\w]+).(?P<format>json)$", PublicBodyDetailView.as_view(), name="publicbody-show_json"),
    url(r"^confirm/$", 'publicbody.views.confirm', name="publicbody-confirm"),
)
