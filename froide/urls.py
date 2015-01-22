from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse
from django.conf.urls.static import static
from django.conf import settings
from django.http import HttpResponseRedirect
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.flatpages.views import flatpage
from django.contrib.sitemaps import Sitemap
from django.utils.translation import ugettext as _

from django.contrib import admin
admin.autodiscover()

from tastypie.api import Api

from froide.publicbody.api import (PublicBodyResource,
    JurisdictionResource, FoiLawResource)
from froide.foirequest.api import (FoiRequestResource,
    FoiMessageResource, FoiAttachmentResource)
from froide.publicbody.views import (PublicBodySitemap, FoiLawSitemap,
                                     JurisdictionSitemap)
from froide.foirequest.views import FoiRequestSitemap

v1_api = Api(api_name='v1')
v1_api.register(PublicBodyResource())
v1_api.register(JurisdictionResource())
v1_api.register(FoiLawResource())
v1_api.register(FoiRequestResource())
v1_api.register(FoiMessageResource())
v1_api.register(FoiAttachmentResource())


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'daily'

    def items(self):
        return ['index', 'foirequest-list']

    def location(self, item):
        return reverse(item)

sitemaps = {
    'publicbody': PublicBodySitemap,
    'foilaw': FoiLawSitemap,
    'jurisdiction': JurisdictionSitemap,
    'foirequest': FoiRequestSitemap,
    'content': StaticViewSitemap
}


SECRET_URLS = getattr(settings, "SECRET_URLS", {})

urlpatterns = patterns('')

if settings.FROIDE_THEME:
    urlpatterns += patterns('',
        url(r'^', include('%s.urls' % settings.FROIDE_THEME)),
    )

if settings.FROIDE_CONFIG.get('api_activated', True):
    urlpatterns += patterns('',
        url(r'^api/', include(v1_api.urls)),
        url(r'api/v1/docs/', include('tastypie_swagger.urls',
            namespace='tastypie_swagger')),
    )

urlpatterns += patterns('',
    # Translators: URL part
    url(r'^$', 'froide.foirequest.views.index', name='index'),
    (r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
    url(r'^dashboard/$', 'froide.foirequest.views.dashboard', name='dashboard')
)

if len(settings.LANGUAGES) > 1:
    urlpatterns += patterns('',
        (r'^i18n/', include('django.conf.urls.i18n'))
    )

urlpatterns += patterns('',
    # Translators: request URL
    url(r'^%s/' % _('make-request'), include('froide.foirequest.make_request_urls')),
    # Translators: URL part
    url(r'^%s/' % _('requests'), include('froide.foirequest.urls')),
    # Translators: request URL
    url(r'^%s/' % _('request'), include('froide.foirequest.request_urls')),
    # Translators: Short-request URL
    url(r"^%s/(?P<obj_id>\d+)$" % _('r'), 'froide.foirequest.views.shortlink', name="foirequest-shortlink"),
    # Translators: Short-request auth URL
    url(r"^%s/(?P<obj_id>\d+)/auth/(?P<code>[0-9a-f]+)/$" % _('r'), 'froide.foirequest.views.auth', name="foirequest-auth"),
    # Translators: follow request URL
    url(r'^%s/' % _('follow'), include('froide.foirequestfollower.urls')),
    # Translators: URL part
    url(r"^%s/(?P<slug>[-\w]+)/$" % _('entity'), 'froide.publicbody.views.show_publicbody',
            name="publicbody-show"),
    url(r"^%s/$" % _('entity'), lambda request: HttpResponseRedirect(reverse('publicbody-list'))),
    # Translators: URL part
    url(r'^%s/' % _('entities'), include('froide.publicbody.urls')),
    # Translators: URL part
    url(r'^%s/' % _('law'), include('froide.publicbody.law_urls')),
    # Translators: URL part
    (r'^%s/' % _('account'), include('froide.account.urls')),
    # Translators: URL part
    (r'^%s/' % _('profile'), include('froide.account.profile_urls')),
    # Translators: URL part
    (r'^%s/' % _('search'), 'froide.foirequest.views.search', {}, "foirequest-search"),
    (r'^comments/', include('django.contrib.comments.urls')),
    # Secret URLs
    url(r'^%s/' % SECRET_URLS.get('admin', 'admin'), include(admin.site.urls))
)

# Translators: URL part
help_url_part = _('help')
# Translators: URL part
about_url_part = _('about')
# Translators: URL part
terms_url_part = _('terms')
# Translators: URL part
privacy_url_part = _('privacy')

urlpatterns += patterns('',
    url(r'^%s/$' % help_url_part, flatpage,
        {'url': '/%s/' % help_url_part}, name='help-index'),
    url(r'^%s/%s/$' % (help_url_part, about_url_part), flatpage,
        {'url': '/%s/%s/' % (help_url_part, about_url_part)}, name='help-about'),
    url(r'^%s/%s/$' % (help_url_part, terms_url_part), flatpage,
        {'url': '/%s/%s/' % (help_url_part, terms_url_part)}, name='help-terms'),
    url(r'^%s/%s/$' % (help_url_part, privacy_url_part), flatpage,
        {'url': '/%s/%s/' % (help_url_part, privacy_url_part)}, name='help-privacy'),
)


if SECRET_URLS.get('postmark_inbound'):
    urlpatterns += patterns('',
        url(r'^postmark/%s/' % SECRET_URLS['postmark_inbound'],
            'froide.foirequest.views.postmark_inbound', name="foirequest-postmark_inbound")
    )

if SECRET_URLS.get('postmark_bounce'):
    urlpatterns += patterns('',
        url(r'^postmark/%s/' % SECRET_URLS['postmark_bounce'],
            'froide.foirequest.views.postmark_bounce', name="foirequest-postmark_bounce")
    )

USE_X_ACCEL_REDIRECT = getattr(settings, 'USE_X_ACCEL_REDIRECT', False)

if USE_X_ACCEL_REDIRECT:
    urlpatterns += patterns('',
        url(r'^%s%s/' % (settings.MEDIA_URL[1:], settings.FOI_MEDIA_PATH),
            include('froide.foirequest.media_urls'))
    )

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Catch all Jurisdiction patterns
urlpatterns += patterns('',
    (r'^(?P<slug>[\w-]+)/', include('froide.publicbody.jurisdiction_urls'))
)


def handler500(request):
    """
    500 error handler which includes ``request`` in the context.
    """

    from django.shortcuts import render
    return render(request, '500.html', {'request': request}, status=500)
