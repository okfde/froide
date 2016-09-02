from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext_lazy as _, ungettext
from django.contrib import messages
from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.template import TemplateDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from haystack.query import SearchQuerySet

from froide.foirequest.models import FoiRequest
from froide.helper.utils import render_400, render_403
from froide.helper.cache import cache_anonymous_page

from .models import (PublicBody,
    PublicBodyTag, FoiLaw, Jurisdiction)
from .csv_import import CSVImporter


def index(request, jurisdiction=None, topic=None):
    if jurisdiction is not None:
        jurisdiction = get_object_or_404(Jurisdiction, slug=jurisdiction)

    if topic is not None:
        topic = get_object_or_404(PublicBodyTag, slug=topic)

    query = request.GET.get('q', '')
    if query:
        publicbodies = SearchQuerySet().models(PublicBody).auto_query(query)
    else:
        publicbodies = PublicBody.objects.get_list()

    if topic:
        publicbodies = publicbodies.filter(tags=topic.name if query else topic)
    if jurisdiction:
        publicbodies = publicbodies.filter(
                jurisdiction=jurisdiction.name if query else jurisdiction)

    page = request.GET.get('page')
    paginator = Paginator(publicbodies, 50)
    try:
        publicbodies = paginator.page(page)
    except PageNotAnInteger:
        publicbodies = paginator.page(1)
    except EmptyPage:
        publicbodies = paginator.page(paginator.num_pages)

    return render(request, 'publicbody/list.html', {
        'object_list': publicbodies,
        'jurisdictions': Jurisdiction.objects.get_list(),
        'jurisdiction': jurisdiction,
        'topic': topic,
        'topics': PublicBodyTag.objects.get_topic_list(),
        'query': query,
    })


@cache_anonymous_page(15 * 60)
def show_jurisdiction(request, slug):
    jurisdiction = get_object_or_404(Jurisdiction, slug=slug)
    context = {
        "object": jurisdiction,
        "pb_count": PublicBody.objects.filter(jurisdiction=jurisdiction).count(),
        "laws": FoiLaw.objects.filter(meta=False,
            jurisdiction=jurisdiction).order_by('priority'),
        "foirequests": FoiRequest.published.filter(jurisdiction=jurisdiction)[:5]
    }
    try:
        return render(request,
            'publicbody/jurisdiction/%s.html' % jurisdiction.slug, context)
    except TemplateDoesNotExist:
        return render(request,
            'publicbody/jurisdiction.html', context)


def show_foilaw(request, slug):
    law = get_object_or_404(FoiLaw, slug=slug)
    context = {"object": law}
    return render(request, 'publicbody/show_foilaw.html', context)


def show_publicbody(request, slug):
    obj = get_object_or_404(PublicBody, slug=slug)
    context = {
        'object': obj,
        'foirequests': FoiRequest.published.filter(
            public_body=obj).order_by('-last_message')[:10],
        'resolutions': FoiRequest.published.get_resolution_count_by_public_body(obj),
        'foirequest_count': FoiRequest.published.filter(public_body=obj).count()
    }
    return render(request, 'publicbody/show.html', context)


@require_POST
def confirm(request):
    if not request.user.is_authenticated:
        return render_403(request)
    if not request.user.is_staff and not request.user.is_superuser:
        return render_403(request)
    try:
        pb = get_object_or_404(PublicBody, pk=int(request.POST.get('public_body', '')))
    except ValueError:
        return render_400(request)
    result = pb.confirm()
    if result is None:
        messages.add_message(request, messages.ERROR,
            _('This request was already confirmed.'))
    else:
        messages.add_message(request, messages.ERROR,
                ungettext('%(count)d message was sent.',
                    '%(count)d messages were sent', result
                    ) % {"count": result})
    return redirect('admin:publicbody_publicbody_change', pb.id)


@require_POST
def import_csv(request):
    if not request.user.is_authenticated:
        return render_403(request)
    if not request.user.is_staff and not request.user.is_superuser:
        return render_403(request)
    if not request.method == 'POST':
        return render_403(request)
    importer = CSVImporter()
    url = request.POST.get('url')
    try:
        if not url:
            raise ValueError(_('You need to provide a url.'))
        importer.import_from_url(url)
    except Exception as e:
        messages.add_message(request, messages.ERROR, str(e))
    else:
        messages.add_message(request, messages.SUCCESS,
            _('Public Bodies were imported.'))
    return redirect('admin:publicbody_publicbody_changelist')


SITEMAP_PROTOCOL = 'https' if settings.SITE_URL.startswith('https') else 'http'


class PublicBodySitemap(Sitemap):
    protocol = SITEMAP_PROTOCOL
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return PublicBody.objects.all()

    def lastmod(self, obj):
        return obj.updated_at


class JurisdictionSitemap(Sitemap):
    protocol = SITEMAP_PROTOCOL
    changefreq = "yearly"
    priority = 0.8

    def items(self):
        return Jurisdiction.objects.all()


class FoiLawSitemap(Sitemap):
    protocol = SITEMAP_PROTOCOL
    changefreq = "yearly"
    priority = 0.3

    def items(self):
        return FoiLaw.objects.all()

    def lastmod(self, obj):
        return obj.updated
