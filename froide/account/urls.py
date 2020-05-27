from django.conf.urls import url, include

from .views import (
    AccountView,
    NewAccountView, AccountConfirmedView,
    account_settings,
    new_terms, logout, login, SignupView, confirm,
    send_reset_password_link, change_password,
    change_user, change_email, go, delete_account,
    make_user_private,
    create_export, download_export,
    CustomPasswordResetConfirmView
)
from .import oauth_urls

urlpatterns = [
    url(r'^', include(oauth_urls, namespace='oauth2_provider')),
    url(r'^$', AccountView.as_view(), name='account-show'),
    url(r'^new/$', NewAccountView.as_view(), name='account-new'),
    url(r'^confirmed/$', AccountConfirmedView.as_view(), name='account-confirmed'),
    url(r'^settings/$', account_settings, name='account-settings'),
    url(r'^terms/$', new_terms, name='account-new_terms'),
    url(r'^logout/$', logout, name='account-logout'),
    url(r'^login/$', login, name='account-login'),
    url(r'^signup/$', SignupView.as_view(), name='account-signup'),
    url(r'^reset/$', send_reset_password_link, name='account-send_reset_password_link'),
    url(r'^change_password/$', change_password, name='account-change_password'),
    url(r'^change_user/$', change_user, name='account-change_user'),
    url(r'^make-private/$', make_user_private, name='account-make_user_private'),
    url(r'^change-email/$', change_email, name='account-change_email'),
    url(r'^delete-account/$', delete_account, name='account-delete_account'),
    url(r'^confirm/(?P<user_id>\d+)/(?P<secret>\w{32})/$', confirm, name='account-confirm'),
    url(r'^confirm/(?P<user_id>\d+)/(?P<request_id>\d+)/(?P<secret>\w{32})/$',
        confirm, name='account-confirm'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        CustomPasswordResetConfirmView.as_view(),
        name='account-password_reset_confirm'),
    url(r'^go/(?P<user_id>\d+)/(?P<secret>\w{32})(?P<url>/.*)$', go,
        name='account-go'),
    url(r'^export/$', create_export,
        name='account-create_export'),
    url(r'^export/download/$', download_export,
        name='account-download_export'),
]
