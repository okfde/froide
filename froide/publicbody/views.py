from typing import Any, Dict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sitemaps import Sitemap
from django.forms.models import model_to_dict
from django.shortcuts import Http404, get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, UpdateView

import markdown
import nh3

from froide.foirequest.models import FoiRequest
from froide.helper.auth import can_moderate_object
from froide.helper.cache import cache_anonymous_page
from froide.helper.search.views import BaseSearchView

from .documents import PublicBodyDocument
from .filters import PublicBodyFilterSet
from .forms import (
    PublicBodyAcceptProposalForm,
    PublicBodyChangeProposalForm,
    PublicBodyProposalForm,
)
from .models import FoiLaw, Jurisdiction, PublicBody, PublicBodyChangeProposal
from .utils import LawExtension


class PublicBodySearch(BaseSearchView):
    search_name = "publicbody"
    template_name = "publicbody/list.html"
    model = PublicBody
    document = PublicBodyDocument
    filterset = PublicBodyFilterSet
    search_url_name = "publicbody-list"

    show_filters = {"jurisdiction", "category", "classification"}
    advanced_filters = {"jurisdiction", "category", "classification"}
    object_template = "publicbody/snippets/publicbody_item.html"
    has_facets = True
    facet_config = {
        "jurisdiction": {
            "model": Jurisdiction,
            "getter": lambda x: x["object"].slug,
            "label_getter": lambda x: x["object"].name,
            "label": _("jurisdictions"),
        }
    }
    search_manager_kwargs = {
        "filter_order": ("jurisdiction", "category"),
        "sub_filters": {"jurisdiction": ("category",)},
    }


@cache_anonymous_page(15 * 60)
def show_jurisdiction(request, slug):
    jurisdiction = get_object_or_404(Jurisdiction, slug=slug, hidden=False)
    context = {
        "object": jurisdiction,
        "pb_count": PublicBody.objects.filter(jurisdiction=jurisdiction).count(),
        "laws": FoiLaw.objects.filter(meta=False, jurisdiction=jurisdiction).order_by(
            "-priority"
        ),
        "foirequests": FoiRequest.published.filter(jurisdiction=jurisdiction)[:5],
    }
    template_names = (
        "publicbody/jurisdiction/%s.html" % jurisdiction.slug,
        "publicbody/jurisdiction.html",
    )
    return render(request, template_names, context)


def show_foilaw(request, slug):
    law = get_object_or_404(FoiLaw.objects.translated(slug=slug))

    legal_text = mark_safe(
        nh3.clean(markdown.markdown(law.legal_text, extensions=[LawExtension()]))
    )

    context = {"object": law, "legal_text": legal_text}
    return render(request, "publicbody/show_foilaw.html", context)


def publicbody_shortlink(request, obj_id):
    obj = get_object_or_404(PublicBody, pk=obj_id)
    return redirect(obj)


class PublicBodyView(DetailView):
    template_name = "publicbody/show.html"

    def get_queryset(self):
        return PublicBody._default_manager.all()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.slug != self.kwargs.get("slug", ""):
            if self._can_access():
                # only redirect if we can access
                return self.get_redirect()
            raise Http404
        if self.kwargs.get("pk") is None:
            return self.get_redirect()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_redirect(self):
        url = self.object.get_absolute_url()
        query = self.request.META["QUERY_STRING"]
        if query:
            return redirect("{}?{}".format(url, query))
        return redirect(url, permanent=True)

    def _can_access(self):
        if not self.object.confirmed:
            not_creator = self.request.user != self.object._created_by
            if not_creator and not can_moderate_object(self.object, self.request):
                return False
        return True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "object": self.object,
                "foirequests": FoiRequest.published.filter(
                    public_body=self.object
                ).order_by("-last_message")[:10],
                "resolutions": FoiRequest.published.get_resolution_count_by_public_body(
                    self.object
                ),
                "foirequest_count": FoiRequest.published.filter(
                    public_body=self.object
                ).count(),
            }
        )
        return ctx


SITEMAP_PROTOCOL = "https" if settings.SITE_URL.startswith("https") else "http"


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


class PublicBodyProposalView(LoginRequiredMixin, CreateView):
    template_name = "publicbody/propose.html"
    form_class = PublicBodyProposalForm

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        self.object = form.save(self.request.user)
        messages.add_message(
            self.request,
            messages.INFO,
            _(
                "Thank you for your proposal. We will send you an email when it has been approved."
            ),
        )
        return redirect(self.get_success_url())

    def handle_no_permission(self):
        messages.add_message(
            self.request,
            messages.WARNING,
            _(
                "You need to register an account and login in order to propose a new public body."
            ),
        )
        return super().handle_no_permission()


class PublicBodyChangeProposalView(LoginRequiredMixin, UpdateView):
    template_name = "publicbody/add_proposal.html"
    form_class = PublicBodyChangeProposalForm
    queryset = PublicBody.objects.all()

    def get_form_kwargs(self) -> Dict[str, Any]:
        """
        Use object to create initial data and reset instance
        """
        kwargs = super().get_form_kwargs()
        fields = self.form_class.Meta.fields
        change_proposal = PublicBodyChangeProposal.objects.filter(
            publicbody=self.object, user=self.request.user
        ).first()
        initial = model_to_dict(change_proposal or self.object, fields=fields)
        kwargs.update(
            {"instance": change_proposal, "initial": initial, "publicbody": self.object}
        )
        return kwargs

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        form.save(self.object, self.request.user)
        messages.add_message(
            self.request,
            messages.INFO,
            _(
                "Thank you for your proposal. We will send you an email when it has been approved."
            ),
        )
        return redirect(self.object)


class PublicBodyAcceptProposalView(LoginRequiredMixin, UpdateView):
    template_name = "publicbody/accept_proposals.html"
    form_class = PublicBodyAcceptProposalForm
    # Default manager gives access to proposed as well
    queryset = PublicBody._default_manager.all()

    def get_object(self):
        obj = super().get_object()
        if not can_moderate_object(obj, self.request):
            raise Http404
        return obj

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        self.object = form.save(
            self.request.user,
            delete_unconfirmed=self.request.POST.get("delete", "0") == "1",
            delete_reason=self.request.POST.get("delete_reason", ""),
            proposal_id=self.request.POST.get("proposal_id"),
            delete_proposals=self.request.POST.getlist("proposal_delete"),
        )
        if self.object is None:
            messages.add_message(
                self.request, messages.INFO, _("The proposal has been deleted.")
            )
            return redirect("publicbody-list")
        messages.add_message(
            self.request, messages.INFO, _("Your change has been applied.")
        )
        return redirect(self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["proposals"] = context["form"].get_proposals()
        return context
