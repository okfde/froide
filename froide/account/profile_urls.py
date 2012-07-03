from django.conf.urls.defaults import patterns

urlpatterns = patterns("froide.account.views",
    (r'^(?P<slug>[-\w\.]+)/$', 'profile', {}, 'account-profile')
)
