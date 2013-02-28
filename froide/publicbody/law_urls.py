from django.conf.urls import patterns, url


urlpatterns = patterns("froide.publicbody.views",
    url(r"^(?P<slug>[-\w]+)/$", 'show_foilaw', name="publicbody-foilaw-show"),
)
