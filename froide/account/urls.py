from django.urls import path, re_path, include

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
    path('', include(oauth_urls, namespace='oauth2_provider')),
    path('', AccountView.as_view(), name='account-show'),
    path('new/', NewAccountView.as_view(), name='account-new'),
    path('confirmed/', AccountConfirmedView.as_view(), name='account-confirmed'),
    path('settings/', account_settings, name='account-settings'),
    path('terms/', new_terms, name='account-new_terms'),
    path('logout/', logout, name='account-logout'),
    path('login/', login, name='account-login'),
    path('signup/', SignupView.as_view(), name='account-signup'),
    path('reset/', send_reset_password_link, name='account-send_reset_password_link'),
    path('change_password/', change_password, name='account-change_password'),
    path('change_user/', change_user, name='account-change_user'),
    path('make-private/', make_user_private, name='account-make_user_private'),
    path('change-email/', change_email, name='account-change_email'),
    path('delete-account/', delete_account, name='account-delete_account'),
    path('confirm/<int:user_id>/<str:secret>/', confirm, name='account-confirm'),
    path('confirm/<int:user_id>/<int:request_id>/<str:secret>/',
        confirm, name='account-confirm'),
    path('reset/<uidb64>/<token>/',
        CustomPasswordResetConfirmView.as_view(),
        name='account-password_reset_confirm'),
    re_path(r'^go/(?P<user_id>\d+)/(?P<secret>\w{32})(?P<url>/.*)$', go,
        name='account-go'),
    path('export/', create_export,
        name='account-create_export'),
    path('export/download/', download_export,
        name='account-download_export'),
]
