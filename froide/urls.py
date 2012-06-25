from django.conf.urls.defaults import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.utils.translation import ugettext as _

from django.contrib import admin
admin.autodiscover()

from publicbody.models import Jurisdiction


SECRET_URLS = getattr(settings, "SECRET_URLS", {})

urlpatterns = patterns('',
    url(r'^$', 'froide.foirequest.views.index', name='index'),
    url(r'^dashboard/$', 'froide.foirequest.views.dashboard', name='dashboard')
)

urlpatterns += patterns('',
    *[(r'^(?P<slug>%s)/' % j.slug,
        include('froide.publicbody.jurisdiction_urls')) for j in Jurisdiction.objects.all()]
)

urlpatterns += patterns('',
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
    (r'^%s/' % _('profile'), include('account.profile_urls')),
    # Translators: URL part
    (r'^%s/' % _('news'), include('foiidea.urls')),
    # Translators: URL part
    (r'^%s/' % _('search'), 'froide.foirequest.views.search', {}, "foirequest-search"),
    # Translators: URL part
    (r'^%s/' % _('help'), include('froide.help_urls')),
    (r'^comments/', include('django.contrib.comments.urls')),
    # Secret URLs
    url(r'^%s/' % SECRET_URLS.get('admin', 'admin'), include(admin.site.urls)),
    (r'^%s/' % SECRET_URLS.get('sentry', 'sentry'), include('sentry.web.urls'))
)

if not settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^%s%s/' % (settings.MEDIA_URL[1:], settings.FOI_MEDIA_PATH),
            include('froide.foirequest.media_urls'))
    )

try:
    from custom_urls import urlpatterns as custom_urlpatterns
    urlpatterns += custom_urlpatterns
except ImportError:
    pass


def handler500(request):
    """
    500 error handler which includes ``request`` in the context.
    """

    from django.shortcuts import render
    return render(request, '500.html', {'request': request}, status=500)


if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
