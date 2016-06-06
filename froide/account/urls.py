from django.conf.urls import url

from .views import (MyRequestsView,
    FollowingRequestsView, account_settings,
    new_terms, logout, login, signup, confirm,
    send_reset_password_link, change_password, password_reset_confirm,
    change_user, change_email, go, delete_account,
)

urlpatterns = [
    url(r'^$', MyRequestsView.as_view(), name='account-show'),
    url(r'^following/$', FollowingRequestsView.as_view(), name='account-following'),
    url(r'^settings/$', account_settings, name='account-settings'),
    url(r'^terms/$', new_terms, name='account-new_terms'),
    url(r'^logout/$', logout, name='account-logout'),
    url(r'^login/$', login, name='account-login'),
    url(r'^signup/$', signup, name='account-signup'),
    url(r'^reset/$', send_reset_password_link, name='account-send_reset_password_link'),
    url(r'^change_password/$', change_password, name='account-change_password'),
    url(r'^change_user/$', change_user, name='account-change_user'),
    url(r'^change-email/$', change_email, name='account-change_email'),
    url(r'^delete-account/$', delete_account, name='account-delete_account'),
    url(r'^confirm/(?P<user_id>\d+)/(?P<secret>\w{32})/$', confirm, name='account-confirm'),
    url(r'^confirm/(?P<user_id>\d+)/(?P<request_id>\d+)/(?P<secret>\w{32})/$',
        confirm, name='account-confirm'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        password_reset_confirm, name='account-password_reset_confirm'),
    url(r'^go/(?P<user_id>\d+)/(?P<secret>\w{32})(?P<url>/.*)$', go,
        name='account-go'),
]
