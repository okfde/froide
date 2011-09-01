from django.conf.urls.defaults import patterns

urlpatterns = patterns("",
    (r'^$', 'account.views.show', {}, 'account-show'),
    (r'^logout/$', 'account.views.logout', {}, 'account-logout'),
    (r'^login/$', 'account.views.login', {}, 'account-login'),
    (r'^signup/$', 'account.views.signup', {}, 'account-signup'),
    (r'^reset/$', 'account.views.send_reset_password_link', {}, 'account-send_reset_password_link'),
    (r'^change_password/$', 'account.views.change_password', {}, 'account-change_password'),
    (r'^change_address/$', 'account.views.change_address', {}, 'account-change_address'),
    (r'^confirm/(?P<user_id>\d+)/(?P<secret>\w{32})/$', 'account.views.confirm', {}, 'account-confirm'),
    (r'^confirm/(?P<user_id>\d+)/(?P<request_id>\d+)/(?P<secret>\w{32})/$', 'account.views.confirm', {}, 'account-confirm'),
    (r'^reset/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        'account.views.password_reset_confirm', {}, 'account-password_reset_confirm'),
    (r'^go/(?P<user_id>\d+)/(?P<secret>\w{32})(?P<url>/.*)$', 'account.views.go', {}, 'account-go'),

)
