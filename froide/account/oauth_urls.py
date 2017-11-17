from django.conf.urls import url
from django.http import HttpResponseRedirect

from oauth2_provider.views import (AuthorizationView, TokenView,
    ApplicationList, ApplicationRegistration, ApplicationDetail,
    ApplicationDelete, ApplicationUpdate)


class CustomAuthorizationView(AuthorizationView):
    def render_to_response(self, context, **kwargs):
        application = context.get('application')
        scopes = context.get('scopes')
        if application is not None and application.can_auto_approve(scopes):
            uri, headers, body, status = self.create_authorization_response(
                request=self.request, scopes=" ".join(scopes),
                credentials=context, allow=True)
            return HttpResponseRedirect(uri)
        context['oauth_request'] = context.get('request')
        context['request'] = self.request
        return super(CustomAuthorizationView, self).render_to_response(context,
                                                                       **kwargs)


urlpatterns = [
    url(r'^authorize/$', CustomAuthorizationView.as_view(), name="authorize"),
    url(r'^token/$', TokenView.as_view(), name="token"),
]


class CustomApplicationUpdate(ApplicationUpdate):
    fields = ['name', 'redirect_uris', 'description', 'homepage', 'image_url']


# Application management views
app_name = 'account'
urlpatterns += [
    url(r'^applications/$', ApplicationList.as_view(), name="list"),
    url(r'^applications/register/$', ApplicationRegistration.as_view(), name="register"),
    url(r'^applications/(?P<pk>\d+)/$', ApplicationDetail.as_view(), name="detail"),
    url(r'^applications/(?P<pk>\d+)/delete/$', ApplicationDelete.as_view(), name="delete"),
    url(r'^applications/(?P<pk>\d+)/update/$', CustomApplicationUpdate.as_view(), name="update"),
]
