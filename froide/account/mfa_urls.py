from django.urls import path

from mfa.views import MFAAuthView, MFACreateView, MFADeleteView, MFAListView

from .auth import recent_auth_required

app_name = "mfa"
urlpatterns = [
    path("", recent_auth_required(MFAListView.as_view()), name="list"),
    path(
        "<int:pk>/delete/", recent_auth_required(MFADeleteView.as_view()), name="delete"
    ),
    path(
        "create/<method>/", recent_auth_required(MFACreateView.as_view()), name="create"
    ),
    path("auth/<method>/", MFAAuthView.as_view(), name="auth"),
]
