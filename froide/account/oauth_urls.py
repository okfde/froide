from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect
from django.urls import path

from oauth2_provider.views import (
    ApplicationDelete,
    ApplicationDetail,
    ApplicationList,
    ApplicationRegistration,
    ApplicationUpdate,
    AuthorizationView,
    AuthorizedTokenDeleteView,
    AuthorizedTokensListView,
    RevokeTokenView,
    TokenView,
)

from .auth import recent_auth_required
from .models import Application


class CustomAuthorizationView(AuthorizationView):
    def render_to_response(self, context, **kwargs):
        application = context.get("application")
        scopes = context.get("scopes")
        if application is not None and application.can_auto_approve(scopes):
            uri, headers, body, status = self.create_authorization_response(
                request=self.request,
                scopes=" ".join(scopes),
                credentials=context,
                allow=True,
            )
            return HttpResponseRedirect(uri)
        context["oauth_request"] = context.get("request")
        context["request"] = self.request
        return super(CustomAuthorizationView, self).render_to_response(
            context, **kwargs
        )


urlpatterns = [
    path("authorize/", CustomAuthorizationView.as_view(), name="authorize"),
    path("token/", TokenView.as_view(), name="token"),
    path("revoke_token/", RevokeTokenView.as_view(), name="revoke-token"),
]


class ApplicationEditMixin:
    fields = [
        "name",
        "description",
        "homepage",
        "redirect_uris",
        "post_logout_redirect_uris",
        "allowed_origins",
        "client_type",
        "authorization_grant_type",
    ]

    def get_form_class(self):
        """
        Returns the form class for the application model
        """
        return modelform_factory(
            Application,
            fields=self.fields,
        )


class CustomApplicationRegistration(ApplicationEditMixin, ApplicationRegistration):
    fields = ApplicationEditMixin.fields + ["client_secret"]


class CustomApplicationUpdate(ApplicationEditMixin, ApplicationUpdate):
    pass


# Application management views
app_name = "account"
urlpatterns += [
    path("applications/", recent_auth_required(ApplicationList.as_view()), name="list"),
    path(
        "applications/register/",
        recent_auth_required(CustomApplicationRegistration.as_view()),
        name="register",
    ),
    path(
        "applications/<int:pk>/",
        recent_auth_required(ApplicationDetail.as_view()),
        name="detail",
    ),
    path(
        "applications/<int:pk>/delete/",
        recent_auth_required(ApplicationDelete.as_view()),
        name="delete",
    ),
    path(
        "applications/<int:pk>/update/",
        recent_auth_required(CustomApplicationUpdate.as_view()),
        name="update",
    ),
]

urlpatterns += [
    path(
        "authorized-tokens/",
        AuthorizedTokensListView.as_view(),
        name="authorized-token-list",
    ),
    path(
        "authorized-tokens/<pk>/delete/",
        AuthorizedTokenDeleteView.as_view(),
        name="authorized-token-delete",
    ),
]
