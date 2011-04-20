from django.conf.urls.defaults import patterns, url

urlpatterns = patterns("",
    (r'^$', 'foirequest.views.make_request', {}, 'foirequest-make_request'),
    (r'^to/(?P<public_body>[-\w]+)/$', 'foirequest.views.make_request', {}, 'foirequest-make_request'),
    (r'^submit$', 'foirequest.views.submit_request', {}, 'foirequest-submit_request'),
    (r'^to/(?P<public_body>[-\w]+)/submit$', 'foirequest.views.submit_request', {}, 'foirequest-submit_request'),
    (r'^success/$', 'foirequest.views.success', {}, 'foirequest-sucess'),
    url(r"^(?P<slug>[-\w]+)/$", 'foirequest.views.show', name="foirequest-show"),
    url(r"^(?P<slug>[-\w]+)/set/public-body/$", 'foirequest.views.set_public_body', name="foirequest-set_public_body"),
    url(r"^(?P<slug>[-\w]+)/set/status/$", 'foirequest.views.set_status', name="foirequest-set_status"),
)
