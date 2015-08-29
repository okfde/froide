from django.conf.urls import patterns

urlpatterns = patterns("froide.account.views",
    (r'^$', 'show', {}, 'account-show'),
    (r'^terms/$', 'new_terms', {}, 'account-new_terms'),
    (r'^settings/$', 'account_settings', {}, 'account-settings'),
    (r'^logout/$', 'logout', {}, 'account-logout'),
    (r'^login/$', 'login', {}, 'account-login'),
    (r'^signup/$', 'signup', {}, 'account-signup'),
    (r'^reset/$', 'send_reset_password_link', {}, 'account-send_reset_password_link'),
    (r'^change_password/$', 'change_password', {}, 'account-change_password'),
    (r'^change_user/$', 'change_user', {}, 'account-change_user'),
    (r'^change-email/$', 'change_email', {}, 'account-change_email'),
    (r'^delete-account/$', 'delete_account', {}, 'account-delete_account'),
    (r'^confirm/(?P<user_id>\d+)/(?P<secret>\w{32})/$', 'confirm', {}, 'account-confirm'),
    (r'^confirm/(?P<user_id>\d+)/(?P<request_id>\d+)/(?P<secret>\w{32})/$', 'confirm',
        {}, 'account-confirm'),
    (r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', 'password_reset_confirm', {},
    'account-password_reset_confirm'),
    (r'^go/(?P<user_id>\d+)/(?P<secret>\w{32})(?P<url>/.*)$', 'go', {}, 'account-go'),

)
