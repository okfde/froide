from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Optional

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from mfa import settings
from mfa.methods import fido2, totp
from mfa.models import MFAKey

from froide.helper.utils import get_redirect, redirect_to_login

from .models import User

RECENT_AUTH_DURATION = timedelta(minutes=30)
RECENT_AUTH_POST_DURATION = timedelta(minutes=40)
LAST_AUTH_KEY = "last_auth"


class MFAMethod(str, Enum):
    FIDO2 = "FIDO2"
    TOTP = "TOTP"


def user_has_mfa(user: User) -> bool:
    if not user.is_authenticated:
        return False
    if not hasattr(user, "_has_mfa"):
        user._has_mfa = MFAKey.objects.filter(user=user).exists()
    return user._has_mfa


def list_mfa_methods(user):
    return MFAKey.objects.filter(user=user).values("name", "method", "id")


def get_mfa_module_for_method(method: MFAMethod):
    if method == MFAMethod.FIDO2:
        return fido2
    elif method == "TOTP":
        return totp
    raise NotImplementedError


def begin_mfa_authenticate_for_method(
    method: MFAMethod, request: HttpRequest, user: User
) -> str:
    module = get_mfa_module_for_method(method)
    data, state = module.authenticate_begin(user)
    request.session["mfa_challenge"] = (data, state)
    return data


def complete_mfa_authenticate_for_method(
    method: str, request: HttpRequest, user: User, request_data: str
) -> None:
    module = get_mfa_module_for_method(method)
    _data, state = request.session.get("mfa_challenge", (None, None))
    module.authenticate_complete(
        state,
        user,
        request_data,
    )


def get_mfa_data(request: HttpRequest) -> Optional[str]:
    return request.session.get("mfa_challenge", (None, None))[0]


def delete_mfa_data(request: HttpRequest) -> None:
    try:
        del request.session["mfa_challenge"]
    except KeyError:
        pass


def start_mfa_auth(request: HttpRequest, user: User, redirect_url: str) -> HttpResponse:
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
    if not user.is_authenticated:
        return False
    if not user.has_usable_password():
        return False
    return user_has_mfa(user)


def set_last_auth(request: HttpRequest) -> None:
    request.session[LAST_AUTH_KEY] = timezone.now().isoformat()


def has_recent_auth(request: HttpRequest) -> bool:
    last_auth_str = request.session.get(LAST_AUTH_KEY)
    if not last_auth_str:
        return False
    try:
        last_auth = datetime.fromisoformat(last_auth_str)
    except ValueError:
        return False
    now = timezone.now()
    diff = now - last_auth
    if request.method == "GET":
        # Shorter duration for GET request
        return diff <= RECENT_AUTH_DURATION
    # Slightly longer duration for other requests
    # So you can submit a form from a page
    return diff <= RECENT_AUTH_POST_DURATION


def requires_recent_auth(request: HttpRequest) -> bool:
    needs_auth = needs_recent_auth(request)
    return needs_auth and not has_recent_auth(request)


def check_recent_auth_decorator(mfa_required=False):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args, **kwargs):
            if not request.user.is_authenticated:
                # in case login required runs later, check here
                return redirect_to_login(request)
            if mfa_required and not user_has_mfa(request.user):
                messages.add_message(
                    request,
                    messages.WARNING,
                    _(
                        "You need to have two-factor login set on your account. Please set it up now."
                    ),
                )
                return get_redirect(request, default="account-settings")
            if requires_recent_auth(request):
                return get_redirect(
                    request,
                    default="account-reauth",
                    params={"next": request.get_full_path()},
                )
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def recent_auth_required(view_func=None, mfa_required=False):
    actual_decorator = check_recent_auth_decorator(mfa_required=mfa_required)

    if view_func:
        return actual_decorator(view_func)

    return actual_decorator


class RecentAuthRequiredAdminMixin:
    @method_decorator(recent_auth_required)
    def change_view(self, *args, **kwargs):
        return super().change_view(*args, **kwargs)

    @method_decorator(recent_auth_required)
    def add_view(self, *args, **kwargs):
        return super().add_view(*args, **kwargs)

    @method_decorator(recent_auth_required)
    def changelist_view(self, *args, **kwargs):
        return super().changelist_view(*args, **kwargs)

    @method_decorator(recent_auth_required)
    def delete_view(self, *args, **kwargs):
        return super().delete_view(*args, **kwargs)

    @method_decorator(recent_auth_required)
    def history_view(self, *args, **kwargs):
        return super().history_view(*args, **kwargs)


class MFAAndRecentAuthRequiredAdminMixin:
    @method_decorator(recent_auth_required(mfa_required=True))
    def change_view(self, *args, **kwargs):
        return super().change_view(*args, **kwargs)

    @method_decorator(recent_auth_required(mfa_required=True))
    def add_view(self, *args, **kwargs):
        return super().add_view(*args, **kwargs)

    @method_decorator(recent_auth_required(mfa_required=True))
    def changelist_view(self, *args, **kwargs):
        return super().changelist_view(*args, **kwargs)

    @method_decorator(recent_auth_required(mfa_required=True))
    def delete_view(self, *args, **kwargs):
        return super().delete_view(*args, **kwargs)

    @method_decorator(recent_auth_required(mfa_required=True))
    def history_view(self, *args, **kwargs):
        return super().history_view(*args, **kwargs)
