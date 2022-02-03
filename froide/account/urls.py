from django.urls import include, path, re_path

from . import oauth_urls
from .views import (
    AccountConfirmedView,
    AccountView,
    CustomPasswordResetConfirmView,
    NewAccountView,
    SignupView,
    account_settings,
    change_account_settings,
    change_email,
    change_password,
    change_profile,
    change_user,
    confirm,
    create_export,
    delete_account,
    download_export,
    go,
    LoginView,
    logout,
    make_user_private,
    new_terms,
    profile_redirect,
    send_reset_password_link,
)

urlpatterns = [
    path("", include(oauth_urls, namespace="oauth2_provider")),
    path("", AccountView.as_view(), name="account-show"),
    path("new/", NewAccountView.as_view(), name="account-new"),
    path("confirmed/", AccountConfirmedView.as_view(), name="account-confirmed"),
    path("profile/", profile_redirect, name="account-profile_redirect"),
    path("settings/", account_settings, name="account-settings"),
    path("terms/", new_terms, name="account-new_terms"),
    path("logout/", logout, name="account-logout"),
    path("login/", LoginView.as_view(), name="account-login"),
    path("signup/", SignupView.as_view(), name="account-signup"),
    path("reset/", send_reset_password_link, name="account-send_reset_password_link"),
    path("change_password/", change_password, name="account-change_password"),
    path("change_user/", change_user, name="account-change_user"),
    path("make-private/", make_user_private, name="account-make_user_private"),
    path("change-email/", change_email, name="account-change_email"),
    path("change-profile/", change_profile, name="account-change_profile"),
    path("change-settings/", change_account_settings, name="account-change_settings"),
    path("delete-account/", delete_account, name="account-delete_account"),
    path("confirm/<int:user_id>/<str:secret>/", confirm, name="account-confirm"),
    path(
        "confirm/<int:user_id>/<int:request_id>/<str:secret>/",
        confirm,
        name="account-confirm",
    ),
    path(
        "reset/<uidb64>/<token>/",
        CustomPasswordResetConfirmView.as_view(),
        name="account-password_reset_confirm",
    ),
    re_path(
        r"^go/(?P<user_id>\d+)/(?P<token>\w{32})(?P<url>/.*)$", go, name="account-go"
    ),
    path("export/", create_export, name="account-create_export"),
    path("export/download/", download_export, name="account-download_export"),
]
