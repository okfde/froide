from django.shortcuts import render, redirect, get_object_or_404, Http404
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.contrib.auth.mixins import LoginRequiredMixin
from django.template import TemplateDoesNotExist
from django.views.generic import FormView

from froide.foirequest.models import FoiRequest
from froide.helper.cache import cache_anonymous_page
from froide.helper.search.views import BaseSearchView

from .models import PublicBody, FoiLaw, Jurisdiction
from .documents import PublicBodyDocument
from .forms import PublicBodyProposalForm
from .filters import PublicBodyFilterSet


FILTER_ORDER = ('jurisdiction', 'category')
SUB_FILTERS = {
    'jurisdiction': ('category',)
}


def get_active_filters(data):
    for key in FILTER_ORDER:
        if not data.get(key):
            continue
        yield key
        sub_filters = SUB_FILTERS.get(key, ())
        for sub_key in sub_filters:
            if data.get(sub_key):
                yield sub_key
                break
        break


def get_filter_data(filter_kwargs, data):
    query = {}
    for key in get_active_filters(filter_kwargs):
        query[key] = filter_kwargs[key]
    data.update(query)
    return data


class PublicBodySearch(BaseSearchView):
    search_name = 'publicbody'
    template_name = 'publicbody/list.html'
    model = PublicBody
    document = PublicBodyDocument
    filterset = PublicBodyFilterSet
    search_url_name = 'publicbody-list'

    show_filters = {
        'jurisdiction', 'category'
    }
    advanced_filters = {
        'jurisdiction', 'category'
    }
    object_template = 'publicbody/snippets/publicbody_item.html'
    has_facets = True
    facet_config = {
        'jurisdiction': {
            'model': Jurisdiction,
            'getter': lambda x: x['object'].slug,
            'label_getter': lambda x: x['object'].name,
            'label': _('jurisdictions'),
        }
    }

    def get_filter_data(self, kwargs, get_dict):
        return get_filter_data(kwargs, get_dict)


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
