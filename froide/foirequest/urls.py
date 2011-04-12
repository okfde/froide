from django.conf.urls.defaults import patterns, url

from foirequest.views import FoiRequestDetailView

urlpatterns = patterns("",
    (r'^$', 'foirequest.views.make_request', {}, 'foirequest-make_request'),
    (r'^to/(?P<public_body>[-\w]+)/$', 'foirequest.views.make_request', {}, 'foirequest-make_request'),
    (r'^submit$', 'foirequest.views.submit_request', {}, 'foirequest-submit_request'),
    (r'^to/(?P<public_body>[-\w]+)/submit$', 'foirequest.views.submit_request', {}, 'foirequest-submit_request'),
    (r'^success/$', 'foirequest.views.success', {}, 'foirequest-sucess'),
    url(r"^(?P<slug>[-\w]+)/$", FoiRequestDetailView.as_view(), name="foirequest-show"),
)
