from django.conf.urls.defaults import patterns

urlpatterns = patterns("",
    (r'^(?P<slug>[-\w\.]+)/$', 'account.views.profile', {}, 'account-profile')
)
