from django.conf.urls import url, include
from django.conf import settings
from django.urls import path

from .views import (
    AccountView,
    NewAccountView, AccountConfirmedView,
    account_settings,
    new_terms, logout, login, SignupView, confirm,
    send_reset_password_link, change_password,
    change_user, change_email, go, delete_account,
    create_export, download_export, ExportFileDetailView,
    CustomPasswordResetConfirmView
)
from .export import EXPORT_MEDIA_PREFIX
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

MEDIA_PATH = settings.MEDIA_URL
# Split off domain and leading slash
if MEDIA_PATH.startswith('http'):
    MEDIA_PATH = MEDIA_PATH.split('/', 3)[-1]
else:
    MEDIA_PATH = MEDIA_PATH[1:]


urlpatterns += [
    path('%s%s/<uuid:token>.zip' % (
        MEDIA_PATH, EXPORT_MEDIA_PREFIX
    ), ExportFileDetailView.as_view(), name='account-download_export_token')
]
