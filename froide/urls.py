from django.conf.urls import include, url
from django.urls import reverse
from django.conf.urls.static import static
from django.conf import settings
from django.http import HttpResponseRedirect
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.flatpages.views import flatpage
from django.contrib.flatpages.sitemaps import FlatPageSitemap
from django.contrib.sitemaps import views as sitemaps_views, Sitemap
from django.utils.translation import pgettext
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap

from rest_framework.routers import DefaultRouter
from rest_framework.schemas import get_schema_view

from froide.account.api_views import ProfileView
from froide.foirequest.api_views import (FoiRequestViewSet, FoiMessageViewSet,
    FoiAttachmentViewSet)
from froide.publicbody.api_views import (ClassificationViewSet,
    CategoryViewSet, PublicBodyViewSet, JurisdictionViewSet, FoiLawViewSet)

from froide.publicbody.views import (PublicBodySitemap, FoiLawSitemap,
                                     JurisdictionSitemap, show_publicbody)
from froide.foirequest.views import FoiRequestSitemap

api_router = DefaultRouter()
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
    'content': StaticViewSitemap,
    'pages': FlatPageSitemap
}


PROTOCOL = settings.SITE_URL.split(':')[0]

for klass in sitemaps.values():
    klass.protocol = PROTOCOL

urlpatterns = [
    url(r'^sitemap\.xml$', sitemaps_views.index,
        {'sitemaps': sitemaps, 'sitemap_url_name': 'sitemaps'}),
    url(r'^sitemap-(?P<section>.+)\.xml$', sitemaps_views.sitemap,
        {'sitemaps': sitemaps}, name='sitemaps')
]


SECRET_URLS = getattr(settings, "SECRET_URLS", {})


if settings.FROIDE_THEME:
    urlpatterns += [
        url(r'^', include('%s.urls' % settings.FROIDE_THEME)),
    ]

if settings.FROIDE_CONFIG.get('api_activated', True):
    schema_view = get_schema_view(title='{name} API'.format(
                                  name=settings.SITE_NAME))
    urlpatterns += [
        url(r'^api/v1/user/', ProfileView.as_view(), name='api-user-profile'),
        url(r'^api/v1/', include((api_router.urls, 'api'))),
        url(r'^api/v1/schema/$', schema_view),
    ]


urlpatterns += [
    # Translators: URL part
    url(r'^', include('froide.foirequest.urls')),
    url(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps}),
]

if len(settings.LANGUAGES) > 1:
    urlpatterns += [
        url(r'^i18n/', include('django.conf.urls.i18n'))
    ]

account = pgettext('url part', 'account')
teams = pgettext('url part', 'teams')

urlpatterns += [
    # Translators: follow request URL
    url(r'^%s/' % pgettext('url part', 'follow'), include('froide.foirequestfollower.urls')),
    # Translators: URL part
    url(r"^%s/(?P<slug>[-\w]+)/$" % pgettext('url part', 'entity'), show_publicbody,
            name="publicbody-show"),
    url(r"^%s/$" % pgettext('url part', 'entity'), lambda request: HttpResponseRedirect(reverse('publicbody-list'))),
    # Translators: URL part
    url(r'^%s/' % pgettext('url part', 'entities'), include('froide.publicbody.urls')),
    # Translators: URL part
    url(r'^%s/' % pgettext('url part', 'law'), include('froide.publicbody.law_urls')),
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

# Translators: URL part
help_url_part = pgettext('url part', 'help')
# Translators: URL part
about_url_part = pgettext('url part', 'about')
# Translators: URL part
terms_url_part = pgettext('url part', 'terms')
# Translators: URL part
privacy_url_part = pgettext('url part', 'privacy')

urlpatterns += [
    url(r'^%s/$' % help_url_part, flatpage,
        {'url': '/%s/' % help_url_part}, name='help-index'),
    url(r'^%s/%s/$' % (help_url_part, about_url_part), flatpage,
        {'url': '/%s/%s/' % (help_url_part, about_url_part)}, name='help-about'),
    url(r'^%s/%s/$' % (help_url_part, terms_url_part), flatpage,
        {'url': '/%s/%s/' % (help_url_part, terms_url_part)}, name='help-terms'),
    url(r'^%s/%s/$' % (help_url_part, privacy_url_part), flatpage,
        {'url': '/%s/%s/' % (help_url_part, privacy_url_part)}, name='help-privacy'),
]


if SECRET_URLS.get('postmark_inbound'):
    from froide.foirequest.views import postmark_inbound

    urlpatterns += [
        url(r'^postmark/%s/' % SECRET_URLS['postmark_inbound'],
            postmark_inbound, name="foirequest-postmark_inbound")
    ]

if SECRET_URLS.get('postmark_bounce'):
    from froide.foirequest.views import postmark_bounce

    urlpatterns += [
        url(r'^postmark/%s/' % SECRET_URLS['postmark_bounce'],
            postmark_bounce, name="foirequest-postmark_bounce")
    ]


if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Catch all Jurisdiction patterns
urlpatterns += [
    url(r'^(?P<slug>[\w-]+)/', include('froide.publicbody.jurisdiction_urls'))
]


def handler500(request):
    """
    500 error handler which includes ``request`` in the context.
    """

    from django.shortcuts import render
    return render(request, '500.html', {'request': request}, status=500)
