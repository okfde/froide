from django.shortcuts import redirect

from mfa import settings


def start_mfa_auth(request, user, redirect_url):
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
