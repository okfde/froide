from datetime import datetime, timedelta

from django.http import HttpRequest
from django.shortcuts import redirect
from django.utils import timezone

from mfa import settings
from mfa.models import MFAKey

RECENT_AUTH_DURATION = timedelta(minutes=30)


def user_has_mfa(user):
    if not user.is_authenticated:
        return False
    if not hasattr(user, "_has_mfa"):
        user._has_mfa = MFAKey.objects.filter(user=user).exists()
    return user._has_mfa


def start_mfa_auth(request: HttpRequest, user, redirect_url):
    """
    Mirrors mfa.views.LoginView
    """

    request.session["mfa_user"] = {
        "pk": user.pk,
        "backend": user.backend,
    }
    request.session["mfa_success_url"] = redirect_url
    for method in settings.METHODS:
        if user.mfakey_set.filter(method=method).exists():
            return redirect("mfa:auth", method)


def needs_recent_auth(request: HttpRequest) -> bool:
    user = request.user
    if not user.has_usable_password():
        return False
    return user_has_mfa(user)


def has_recent_auth(request: HttpRequest) -> bool:
    last_auth_str = request.session.get("last_auth")
    if not last_auth_str:
        return False
    try:
        last_auth = datetime.fromisoformat(last_auth_str)
    except ValueError:
        return False
    now = timezone.now()
    diff = now - last_auth
    return diff <= RECENT_AUTH_DURATION


def requires_recent_auth(request: HttpRequest) -> bool:
    needs_auth = needs_recent_auth(request)
    return needs_auth and not has_recent_auth(request)


def recent_auth_required(view_func):
    def check_recent_auth(request: HttpRequest, *args, **kwargs):
        if requires_recent_auth(request):
            return redirect("account-reauth")
        return view_func(request, *args, **kwargs)

    return check_recent_auth
