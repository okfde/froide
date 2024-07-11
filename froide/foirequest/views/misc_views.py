from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.http import HttpResponse
from django.shortcuts import render

from froide.frontpage.models import FeaturedRequest
from froide.helper.cache import cache_anonymous_page
from froide.publicbody.models import PublicBody

from ..decorators import allow_read_foirequest_authenticated
from ..foi_mail import package_foirequest
from ..models import FoiRequest
from ..pdf_generator import FoiRequestPDFGenerator


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


@allow_read_foirequest_authenticated
def download_foirequest_zip(request, foirequest):
    response = HttpResponse(
        package_foirequest(foirequest), content_type="application/zip"
    )
    name = "%s-%s" % (
        foirequest.slug,
        foirequest.pk,
    )
    response["Content-Disposition"] = 'attachment; filename="%s.zip"' % name
    return response


@allow_read_foirequest_authenticated
def download_foirequest_pdf(request, foirequest):
    pdf_generator = FoiRequestPDFGenerator(foirequest)
    response = HttpResponse(
        pdf_generator.get_pdf_bytes(), content_type="application/pdf"
    )
    name = "%s-%s" % (
        foirequest.slug,
        foirequest.pk,
    )
    response["Content-Disposition"] = 'attachment; filename="%s.pdf"' % name
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
