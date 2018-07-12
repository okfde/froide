from django.shortcuts import render, redirect, get_object_or_404, Http404
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.contrib.auth.mixins import LoginRequiredMixin
from django.template import TemplateDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import FormView

from haystack.query import SearchQuerySet

from froide.foirequest.models import FoiRequest
from froide.helper.cache import cache_anonymous_page

from .models import PublicBody, Category, FoiLaw, Jurisdiction
from .forms import PublicBodyProposalForm


def index(request, jurisdiction=None, topic=None):
    if jurisdiction is not None:
        jurisdiction = get_object_or_404(Jurisdiction, slug=jurisdiction)

    if topic is not None:
        topic = get_object_or_404(Category, slug=topic)

    query = request.GET.get('q', '')
    if query:
        publicbodies = SearchQuerySet().models(PublicBody).auto_query(query)
    else:
        publicbodies = PublicBody.objects.get_list()

    if topic:
        publicbodies = publicbodies.filter(categories=topic.name if query else topic)
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
        'topics': Category.objects.get_category_list(),
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


def publicbody_shortlink(request, obj_id):
    obj = get_object_or_404(PublicBody, pk=obj_id)
    return redirect(obj)


def show_publicbody(request, slug):
    obj = get_object_or_404(PublicBody._default_manager, slug=slug)
    if not obj.confirmed:
        if request.user != obj._created_by and not request.user.is_staff:
            raise Http404
    context = {
        'object': obj,
        'foirequests': FoiRequest.published.filter(
            public_body=obj).order_by('-last_message')[:10],
        'resolutions': FoiRequest.published.get_resolution_count_by_public_body(obj),
        'foirequest_count': FoiRequest.published.filter(public_body=obj).count()
    }
    return render(request, 'publicbody/show.html', context)


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


class PublicBodyProposalView(LoginRequiredMixin, FormView):
    template_name = 'publicbody/propose.html'
    form_class = PublicBodyProposalForm

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        self.object = form.save(self.request.user)
        messages.add_message(
            self.request, messages.INFO,
            _('Thank you for your proposal. We will send you an email when it has been approved.')
        )
        return super(PublicBodyProposalView, self).form_valid(form)

    def handle_no_permission(self):
        messages.add_message(
            self.request, messages.WARNING,
            _('You need to register an account and login in order to propose a new public body.')
        )
        return super(PublicBodyProposalView, self).handle_no_permission()
