from django.conf.urls import include, url
from django.urls import reverse
from django.conf.urls.static import static
from django.conf import settings
from django.http import HttpResponseRedirect
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.flatpages.sitemaps import FlatPageSitemap
from django.contrib.sitemaps import views as sitemaps_views, Sitemap
from django.utils.translation import pgettext
from django.contrib import admin

from rest_framework.schemas import get_schema_view

from froide.account.api_views import ProfileView
from froide.foirequest.api_views import (FoiRequestViewSet, FoiMessageViewSet,
    FoiAttachmentViewSet)
from froide.publicbody.api_views import (ClassificationViewSet,
    CategoryViewSet, PublicBodyViewSet, JurisdictionViewSet, FoiLawViewSet)
from froide.georegion.api_views import GeoRegionViewSet

from froide.publicbody.views import (PublicBodySitemap, FoiLawSitemap,
                                     JurisdictionSitemap, show_publicbody,
                                     publicbody_shortlink)
from froide.foirequest.views import FoiRequestSitemap, index, dashboard


from froide.helper import api_router


def handler500(request):
    """
    500 error handler which includes ``request`` in the context.
    """

    from django.shortcuts import render
    return render(request, '500.html', {'request': request}, status=500)


api_router.register(r'request', FoiRequestViewSet, base_name='request')
api_router.register(r'message', FoiMessageViewSet, base_name='message')
api_router.register(r'attachment', FoiAttachmentViewSet,
                    base_name='attachment')
api_router.register(r'publicbody', PublicBodyViewSet, base_name='publicbody')
api_router.register(r'category', CategoryViewSet, base_name='category')
api_router.register(r'classification', ClassificationViewSet,
                    base_name='classification')
api_router.register(r'jurisdiction', JurisdictionViewSet,
                    base_name='jurisdiction')
api_router.register(r'law', FoiLawViewSet, base_name='law')
api_router.register(r'georegion', GeoRegionViewSet, base_name='georegion')


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'daily'

    def items(self):
        return ['foirequest-list']

    def location(self, item):
        return reverse(item)


sitemaps = {
    'publicbody': PublicBodySitemap,
    'foilaw': FoiLawSitemap,
    'jurisdiction': JurisdictionSitemap,
    'foirequest': FoiRequestSitemap,
    'content': StaticViewSitemap,
    'pages': FlatPageSitemap
}


PROTOCOL = settings.SITE_URL.split(':')[0]

for klass in sitemaps.values():
    klass.protocol = PROTOCOL

sitemap_urlpatterns = [
    url(r'^sitemap\.xml$', sitemaps_views.index,
        {'sitemaps': sitemaps, 'sitemap_url_name': 'sitemaps'}),
    url(r'^sitemap-(?P<section>.+)\.xml$', sitemaps_views.sitemap,
        {'sitemaps': sitemaps}, name='sitemaps')
]

froide_urlpatterns = []

SECRET_URLS = getattr(settings, "SECRET_URLS", {})

if settings.FROIDE_CONFIG.get('api_activated', True):
    schema_view = get_schema_view(title='{name} API'.format(
                                  name=settings.SITE_NAME))
    froide_urlpatterns += [
        url(r'^api/v1/user/', ProfileView.as_view(), name='api-user-profile'),
        url(r'^api/v1/', include((api_router.urls, 'api'))),
        url(r'^api/v1/schema/$', schema_view),
    ]


froide_urlpatterns += [
    # Translators: URL part
    url(r'^', include('froide.foirequest.urls')),
]

if len(settings.LANGUAGES) > 1:
    froide_urlpatterns += [
        url(r'^i18n/', include('django.conf.urls.i18n'))
    ]

account = pgettext('url part', 'account')
documents = pgettext('url part', 'documents')
teams = pgettext('url part', 'teams')

froide_urlpatterns += [
    # Translators: follow request URL
    url(r'^%s/' % pgettext('url part', 'follow'), include('froide.foirequestfollower.urls')),

    url(r"^%s/(?P<obj_id>\d+)/?$" % pgettext('url part', 'b'),
        publicbody_shortlink, name="publicbody-publicbody_shortlink"),
    # Translators: URL part
    url(r"^%s/(?P<slug>[-\w]+)/$" % pgettext('url part', 'entity'), show_publicbody,
            name="publicbody-show"),
    url(r"^%s/$" % pgettext('url part', 'entity'),
        lambda request: HttpResponseRedirect(reverse('publicbody-list'))),
    # Translators: URL part
    url(r'^%s/' % pgettext('url part', 'entities'), include('froide.publicbody.urls')),
    # Translators: URL part
    url(r'^%s/' % pgettext('url part', 'law'), include('froide.publicbody.law_urls')),
    # Translators: URL part
    url(r'^%s/' % documents, include('froide.document.urls')),
    # Translators: URL part
    url(r'^%s/' % account, include('froide.account.urls')),
    # Translators: URL part
    url(r'^%s/%s/' % (account, teams), include('froide.team.urls')),
    # Translators: URL part
    url(r'^%s/' % pgettext('url part', 'profile'), include('froide.account.profile_urls')),
    # Translators: URL part
    url(r'^comments/', include('django_comments.urls')),
    # Secret URLs
    url(r'^%s/' % SECRET_URLS.get('admin', 'admin'), admin.site.urls)
]

if SECRET_URLS.get('postmark_inbound'):
    from froide.foirequest.views import postmark_inbound

    froide_urlpatterns += [
        url(r'^postmark/%s/' % SECRET_URLS['postmark_inbound'],
            postmark_inbound, name="foirequest-postmark_inbound")
    ]

if SECRET_URLS.get('postmark_bounce'):
    from froide.foirequest.views import postmark_bounce

    froide_urlpatterns += [
        url(r'^postmark/%s/' % SECRET_URLS['postmark_bounce'],
            postmark_bounce, name="foirequest-postmark_bounce")
    ]


if settings.DEBUG:
    froide_urlpatterns += staticfiles_urlpatterns()
    froide_urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

if settings.DEBUG:
    try:
        import debug_toolbar
        froide_urlpatterns = [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ] + froide_urlpatterns
    except ImportError:
        pass


# Translators: URL part
jurisdiction_part = pgettext('url part', 'jurisdiction')

jurisdiction_urls = [
    url(r'^%s/(?P<slug>[\w-]+)/' % jurisdiction_part,
        include('froide.publicbody.jurisdiction_urls'))
]

urlpatterns = froide_urlpatterns + [
    url(r'^$', index, name='index'),
    url(r'^dashboard/$', dashboard, name='dashboard'),
] + sitemap_urlpatterns + jurisdiction_urls
