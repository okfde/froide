from django.conf.urls.defaults import patterns, url


urlpatterns = patterns("",
    url(r"^(?P<slug>[-\w]+)$", 'publicbody.views.show_foilaw', name="publicbody-foilaw-show"),
)
