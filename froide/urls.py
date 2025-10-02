from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps import views as sitemaps_views
from django.template.response import TemplateResponse
from django.urls import include, path, reverse
from django.utils.translation import pgettext_lazy

from drf_spectacular.views import SpectacularJSONAPIView, SpectacularSwaggerView

from froide.account.api_views import ProfileView, UserPreferenceView
from froide.account.views import bad_login_view_redirect
from froide.document.urls import document_media_urlpatterns
from froide.foirequest.views import FoiRequestSitemap, index
from froide.publicbody.views import (
    FoiLawSitemap,
    JurisdictionSitemap,
    PublicBodySitemap,
)

from .api import api_router


def handler500(request):
    """
    500 error handler which includes ``request`` in the context.
    """

    from django.shortcuts import render

    return render(request, "500.html", {"request": request}, status=500)


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "daily"

    def items(self):
        return ["foirequest-list"]

    def location(self, item):
        return reverse(item)


sitemaps = {
    "publicbody": PublicBodySitemap,
    "foilaw": FoiLawSitemap,
    "jurisdiction": JurisdictionSitemap,
    "foirequest": FoiRequestSitemap,
    "content": StaticViewSitemap,
}


PROTOCOL = settings.SITE_URL.split(":")[0]

for klass in sitemaps.values():
    klass.protocol = PROTOCOL

sitemap_urlpatterns = [
    path(
        "sitemap.xml",
        sitemaps_views.index,
        {"sitemaps": sitemaps, "sitemap_url_name": "sitemaps"},
    ),
    path(
        "sitemap-<str:section>.xml",
        sitemaps_views.sitemap,
        {"sitemaps": sitemaps},
        name="sitemaps",
    ),
]

froide_urlpatterns = []
api_urlpatterns = []
SECRET_URLS = getattr(settings, "SECRET_URLS", {})

if settings.FROIDE_CONFIG.get("api_activated", True):
    api_urlpatterns = [
        path("api/v1/user/", ProfileView.as_view(), name="api-user-profile"),
        path(
            "api/v1/userpreference/<str:key>/",
            UserPreferenceView.as_view(),
            name="api-user-preference",
        ),
        path("api/v1/", include((api_router.urls, "api"))),
        path(
            "api/v1/schema/",
            SpectacularJSONAPIView.as_view(),
            name="schema",
        ),
        path(
            "api/v1/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    ]


froide_urlpatterns += [
    # Translators: URL part
    path("", include("froide.foirequest.urls")),
]

if len(settings.LANGUAGES) > 1:
    froide_urlpatterns += [path("i18n/", include("django.conf.urls.i18n"))]

froide_urlpatterns += [
    # Translators: follow request URL
    path(
        pgettext_lazy("url part", "follow/"),
        include("froide.follow.urls", namespace="follow"),
    ),
    path("", include("froide.publicbody.urls")),
    path(pgettext_lazy("url part", "law/"), include("froide.publicbody.law_urls")),
    path(pgettext_lazy("url part", "documents/"), include("froide.document.urls")),
    path(pgettext_lazy("url part", "account/teams/"), include("froide.team.urls")),
    path(pgettext_lazy("url part", "account/proofs/"), include("froide.proof.urls")),
    path(pgettext_lazy("url part", "account/"), include("froide.account.urls")),
    path("", include("froide.account.export_urls")),
    path(
        pgettext_lazy("url part", "account/access-token/"),
        include("froide.accesstoken.urls"),
    ),
    path(pgettext_lazy("url part", "profile/"), include("froide.account.profile_urls")),
    path(pgettext_lazy("url part", "comments/"), include("django_comments.urls")),
    path(pgettext_lazy("url part", "problem/"), include("froide.problem.urls")),
    path(
        pgettext_lazy("url part", "moderation/"),
        include("froide.problem.moderation_urls"),
    ),
    path(pgettext_lazy("url part", "letter/"), include("froide.letter.urls")),
    path("guide/", include("froide.guide.urls")),
    path("500/", lambda request: TemplateResponse(request, "500.html")),
    path(
        pgettext_lazy("url part", "organization/"), include("froide.organization.urls")
    ),
]

froide_urlpatterns += document_media_urlpatterns

admin_urls = [
    # Disable admin login page, by overriding URL and redirecting
    path("%s/login/" % SECRET_URLS.get("admin", "admin"), bad_login_view_redirect),
    path("%s/" % SECRET_URLS.get("admin", "admin"), admin.site.urls),
]


if settings.SERVE_MEDIA:
    froide_urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    try:
        import debug_toolbar

        froide_urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + froide_urlpatterns
    except ImportError:
        pass


jurisdiction_urls = [
    path(
        pgettext_lazy("url part", "jurisdiction/<slug:slug>/"),
        include("froide.publicbody.jurisdiction_urls"),
    )
]

urlpatterns = (
    froide_urlpatterns
    + [
        path("", index, name="index"),
    ]
    + api_urlpatterns
    + sitemap_urlpatterns
    + jurisdiction_urls
    + admin_urls
)
