from django.contrib.auth.views import redirect_to_login
from django.contrib.flatpages.views import flatpage
from django.core.exceptions import ImproperlyConfigured

from .views import new_terms


class AcceptNewTermsMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not hasattr(request, "user"):
            raise ImproperlyConfigured(
                "AcceptNewTermsMiddleware depends on AuthenticationMiddleware"
            )
        if not request.user.is_authenticated or request.user.terms:
            return None
        if view_func == new_terms or view_func == flatpage:
            return None
        return redirect_to_login(request.path, login_url="account-new_terms")
