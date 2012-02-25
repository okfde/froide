from django.conf.urls.defaults import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.utils.translation import ugettext as _

from django.contrib import admin
admin.autodiscover()

from django.contrib import databrowse
from publicbody.models import PublicBody, FoiLaw

databrowse.site.register(PublicBody)
databrowse.site.register(FoiLaw)

SECRET_URLS = getattr(settings, "SECRET_URLS", {})

urlpatterns = patterns('',
    url(r'^$', 'froide.foirequest.views.index', name='index'),
    url(r'^dashboard/$', 'froide.foirequest.views.dashboard', name='dashboard'),
    # Translators: request URL
    url(r'^%s/' % _('make-request'), include('froide.foirequest.make_request_urls')),
    # Translators: URL part
    url(r'^%s/' % _('requests'), include('froide.foirequest.urls')),
    # Translators: request URL
    url(r'^%s/' % _('request'), include('froide.foirequest.request_urls')),
    # Translators: follow request URL
    url(r'^%s/' % _('follow'), include('froide.foirequestfollower.urls')),


    # Translators: URL part
    url(r'^%s/' % _('entity'), include('froide.publicbody.urls')),
    # Translators: URL part
    url(r'^%s/' % _('law'), include('froide.publicbody.law_urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Translators: URL part
    (r'^%s/' % _('account'), include('account.urls')),
    # Translators: URL part
    (r'^%s/' % _('search'), 'froide.foirequest.views.search', {}, "foirequest-search"),
    # Translators: URL part
    (r'^%s/' % _('help'), include('froide.help_urls')),
    (r'^comments/', include('django.contrib.comments.urls')),
    # Secret URLs
    url(r'^%s/' % SECRET_URLS.get('admin', 'admin'), include(admin.site.urls)),
    (r'^%s/' % SECRET_URLS.get('sentry', 'sentry'), include('sentry.web.urls')),
    (r'^%s/(.*)' % SECRET_URLS.get('databrowse', 'databrowse'),
            user_passes_test(lambda u: u.is_superuser,
                login_url="/account/login/")(databrowse.site.root)),
)

def handler500(request):
    """
    500 error handler which includes ``request`` in the context.
    """
   
    from django.shortcuts import render

    return render(request, '500.html', {'request': request}, status=500)


if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
