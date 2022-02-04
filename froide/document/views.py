import json

from django.conf import settings
from django.contrib import messages
from django.shortcuts import Http404, get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from crossdomainmedia import CrossDomainMediaMixin
from elasticsearch_dsl.query import Q
from filingcabinet.models import Page
from taggit.models import Tag

from froide.helper.search.views import BaseSearchView
from froide.team.models import Team

from .auth import DocumentCrossDomainMediaAuth
from .documents import PageDocument
from .feeds import DocumentSearchFeed
from .filters import PageDocumentFilterset
from .forms import DocumentUploadForm
from .models import Document


class DocumentSearchView(BaseSearchView):
    search_name = "document"
    template_name = "document/search.html"
    object_template = "document/result_item.html"
    show_filters = {
        "jurisdiction",
        "campaign",
    }
    advanced_filters = {"jurisdiction", "campaign"}
    has_facets = True
    facet_config = {
        "tags": {
            "model": Tag,
            "getter": lambda x: x["object"].slug,
            "query_param": "tag",
            "label_getter": lambda x: x["object"].name,
            "label": _("tags"),
        }
    }
    model = Page
    document = PageDocument
    filterset = PageDocumentFilterset
    search_url_name = "document-search"
    select_related = ("document",)

    def get_base_search(self):
        # FIXME: add team
        q = Q("term", public=True)
        if self.request.user.is_authenticated:
            q |= Q("term", user=self.request.user.pk)
            q |= Q("terms", team=Team.objects.get_list_for_user(self.request.user))
        return super().get_base_search().filter(q).filter("term", portal=0)


class DocumentSearchFeedView(DocumentSearchView):
    def get_search(self):
        return super().get_search().sort("-created_at")

    def render_to_response(self, context, **response_kwargs):
        feed_obj = DocumentSearchFeed(context["object_list"], data=self.filtered_objs)
        return feed_obj(self.request)


class DocumentFileDetailView(CrossDomainMediaMixin, DetailView):
    """
    Add the CrossDomainMediaMixin
    and set your custom media_auth_class
    """

    media_auth_class = DocumentCrossDomainMediaAuth

    def get_object(self):
        uid = self.kwargs["uuid"]
        if (
            uid[0:2] != self.kwargs["u1"]
            or uid[2:4] != self.kwargs["u2"]
            or uid[4:6] != self.kwargs["u3"]
        ):
            raise Http404
        return get_object_or_404(Document, uid=uid)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filename"] = self.kwargs["filename"]
        return ctx

    def redirect_to_media(self, mauth):
        """
        Force direct links on main domain that are not
        refreshing a token to go to the objects page
        """
        # Check file authorization first
        url = mauth.get_authorized_media_url(self.request)

        # Check if download is requested
        download = self.request.GET.get("download")
        if download is None:
            # otherwise redirect to document page
            return redirect(self.object.get_absolute_url(), permanent=True)

        return redirect(url)

    def send_media_file(self, mauth):
        response = super().send_media_file(mauth)
        response["Link"] = '<{}>; rel="canonical"'.format(
            self.object.get_absolute_domain_url()
        )
        return response


def upload_documents(request):
    from froide.upload.forms import get_uppy_i18n

    if not request.user.is_staff:
        return redirect("/")

    if request.method == "POST":
        form = DocumentUploadForm(request.POST)
        if form.is_valid():
            doc_count = form.save(request.user)
            messages.add_message(
                request,
                messages.SUCCESS,
                _("%s file(s) uploaded successfully.") % doc_count,
            )
            return redirect(request.get_full_path())
    else:
        form = DocumentUploadForm()

    config = json.dumps(
        {
            "settings": {
                "tusChunkSize": settings.DATA_UPLOAD_MAX_MEMORY_SIZE - (500 * 1024)
            },
            "i18n": {
                "uppy": get_uppy_i18n(),
                "createDocuments": gettext("Create documents now"),
            },
            "url": {
                "tusEndpoint": reverse("api:upload-list"),
            },
        }
    )
    return render(request, "document/upload.html", {"form": form, "config": config})
