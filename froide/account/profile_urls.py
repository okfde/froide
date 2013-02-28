from django.conf.urls import patterns

urlpatterns = patterns("froide.account.views",
    (r'^(?P<slug>[-\w\.]+)/$', 'profile', {}, 'account-profile')
)
