from django.conf.urls.defaults import patterns, url

urlpatterns = patterns("",
    (r'^$', 'account.views.show', {}, 'account-show'),
    (r'^logout/$', 'account.views.logout', {}, 'account-logout'),
    (r'^login/$', 'account.views.login', {}, 'account-login'),
    (r'^signup/$', 'account.views.signup', {}, 'account-signup'),
    (r'^confirm/(?P<user_id>\d+)/(?P<secret>\w{32})/$', 'account.views.confirm', {}, 'account-confirm'),
    (r'^confirm/(?P<user_id>\d+)/(?P<request_id>\d+)/(?P<secret>\w{32})/$', 'account.views.confirm', {}, 'account-confirm'),

)

