from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sitemaps import Sitemap
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from froide.frontpage.models import FeaturedRequest
from froide.helper.cache import cache_anonymous_page
from froide.helper.utils import render_403
from froide.publicbody.models import PublicBody

from ..auth import can_read_foirequest_authenticated
from ..foi_mail import package_foirequest
from ..models import FoiRequest
from ..pdf_generator import FoiRequestPDFGenerator

User = get_user_model()


@cache_anonymous_page(15 * 60)
def index(request):
    successful_foi_requests = FoiRequest.published.successful()[:8]
    unsuccessful_foi_requests = FoiRequest.published.unsuccessful()[:8]
    featured = FeaturedRequest.objects.getFeatured()
    return render(
        request,
        "index.html",
        {
            "featured": featured,
            "successful_foi_requests": successful_foi_requests,
            "unsuccessful_foi_requests": unsuccessful_foi_requests,
            "foicount": FoiRequest.objects.get_send_foi_requests().count(),
            "pbcount": PublicBody.objects.get_list().count(),
        },
    )


def download_foirequest_zip(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not can_read_foirequest_authenticated(foirequest, request):
        return render_403(request)
    response = HttpResponse(
        package_foirequest(foirequest), content_type="application/zip"
    )
    response["Content-Disposition"] = 'attachment; filename="%s.zip"' % foirequest.pk
    return response


def download_foirequest_pdf(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not can_read_foirequest_authenticated(foirequest, request):
        return render_403(request)
    pdf_generator = FoiRequestPDFGenerator(foirequest)
    response = HttpResponse(
        pdf_generator.get_pdf_bytes(), content_type="application/pdf"
    )
    response["Content-Disposition"] = 'attachment; filename="%s.pdf"' % foirequest.pk
    return response


SITEMAP_PROTOCOL = "https" if settings.SITE_URL.startswith("https") else "http"


class FoiRequestSitemap(Sitemap):
    protocol = SITEMAP_PROTOCOL
    changefreq = "hourly"
    priority = 0.5

    def items(self):
        return FoiRequest.published.filter(same_as__isnull=True)

    def lastmod(self, obj):
        return obj.last_message
