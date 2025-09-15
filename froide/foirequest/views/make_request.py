import json
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import decorator_from_middleware, method_decorator
from django.utils.html import linebreaks
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, FormView, TemplateView

from froide.account.forms import AddressForm, NewUserForm
from froide.campaign.models import Campaign
from froide.georegion.models import GeoRegion
from froide.helper.auth import get_read_queryset
from froide.helper.content_urls import get_content_url
from froide.helper.utils import update_query_params
from froide.proof.forms import ProofMessageForm
from froide.publicbody.forms import MultiplePublicBodyForm, PublicBodyForm
from froide.publicbody.models import PublicBody
from froide.publicbody.serializers import PublicBodyListSerializer
from froide.publicbody.widgets import get_widget_context

from ..forms import RequestForm
from ..models import FoiProject, FoiRequest, RequestDraft
from ..services import CreateRequestService, SaveDraftService
from ..utils import check_throttle
from ..validators import PLACEHOLDER_MARKER

csrf_middleware_class = import_string(
    getattr(
        settings, "FROIDE_CSRF_MIDDLEWARE", "django.middleware.csrf.CsrfViewMiddleware"
    )
)

csrf_protect = decorator_from_middleware(csrf_middleware_class)

USER_VAR_MAX_KEY_LENGTH = 30
USER_VAR_MAX_COUNT = 20


class FakePublicBodyForm(object):
    def __init__(self, publicbodies):
        self.publicbodies = publicbodies
        self.valid = False

    def is_valid(self):
        self.valid = True
        return True

    @property
    def is_multi(self):
        return len(self.publicbodies) > 1

    def get_publicbodies(self):
        assert self.valid
        return self.publicbodies

    def as_json(self):
        return json.dumps(
            {"fields": {"publicbody": {}}, "errors": {}, "nonFieldErrors": []}
        )


def replace_user_vars(template_string, user_vars):
    for key, val in user_vars.items():
        template_string = template_string.replace(key, val)
    return template_string


@method_decorator(csrf_exempt, name="dispatch")
class MakeRequestView(FormView):
    form_class = RequestForm
    template_name = "foirequest/request.html"
    FORM_CONFIG_PARAMS = (
        "hide_similar",
        "hide_public",
        "hide_draft",
        "hide_publicbody",
        "hide_full_text",
        "hide_editing",
    )

    draft = None

    def get_initial(self):
        request = self.request
        initial = {
            "subject": request.GET.get("subject", ""),
            "body": request.GET.get("body", ""),
            "reference": request.GET.get("ref", ""),
            "tags": request.GET.get("tags", ""),
            "redirect_url": request.GET.get("redirect", ""),
        }
        user_vars = self.get_user_template_vars()
        if user_vars:
            initial["subject"] = replace_user_vars(initial["subject"], user_vars)
            initial["body"] = replace_user_vars(initial["body"], user_vars)

        if "draft" in request.GET:
            initial["draft"] = request.GET["draft"]

        if initial.get("hide_public"):
            initial["public"] = True
        if "public" in request.GET:
            initial["public"] = request.GET["public"] == "1"

        if "law_type" in request.GET:
            initial["law_type"] = request.GET["law_type"]

        if "full_text" in request.GET:
            initial["full_text"] = request.GET["full_text"] == "1"

        initial["language"] = request.LANGUAGE_CODE

        initial["jurisdiction"] = request.GET.get("jurisdiction", None)
        initial.update(self.get_form_config_initial())
        return initial

    def get_user_template_vars(self):
        user_vars = {}
        for key in self.request.GET:
            if key.startswith("$") and len(key) < USER_VAR_MAX_KEY_LENGTH:
                user_vars[key] = self.request.GET[key]
        if len(user_vars) > USER_VAR_MAX_COUNT:
            return {}
        return user_vars

    def get_js_context(self):
        ctx = {
            "settings": {
                "user_can_hide_web": settings.FROIDE_CONFIG.get("user_can_hide_web"),
                "user_can_create_batch": self.can_create_batch(),
                "non_meaningful_subject_regex": settings.FROIDE_CONFIG.get(
                    "non_meaningful_subject_regex", []
                ),
                "address_regex": settings.FROIDE_CONFIG.get("address_regex", ""),
            },
            "url": {
                "searchRequests": reverse("api:request-search"),
                "listJurisdictions": reverse("api:jurisdiction-list"),
                "listCategories": reverse("api:category-list"),
                "listClassifications": reverse("api:classification-list"),
                "listGeoregions": reverse("api:georegion-list"),
                "listPublicBodies": reverse("api:publicbody-list"),
                "listLaws": reverse("api:law-list"),
                "search": reverse("foirequest-search"),
                "user": reverse("api-user-profile"),
                "makeRequestTo": reverse(
                    "foirequest-make_request", kwargs={"publicbody_ids": "0"}
                ),
                "makeRequest": reverse("foirequest-make_request"),
                "helpRequestWhat": get_content_url("help_request_what"),
                "helpRequestWhatNot": get_content_url("help_request_what_not"),
                "helpRequestPublic": get_content_url("help_request_public"),
                "helpRequestPrivacy": get_content_url("help_request_privacy"),
            },
            "i18n": {
                "publicBodiesFound": [
                    _("one public body found"),
                    _("{count} public bodies found").format(count="${count}"),
                ],
                "publicBodiesChosen": [
                    _("one public body chosen"),
                    _("{count} public bodies chosen").format(count="${count}"),
                ],
                "publicBodiesCount": [
                    _("one public body"),
                    _("{count} public bodies").format(count="${count}"),
                ],
                "requestCount": [
                    pgettext("js", "one request"),
                    _("{count} requests").format(count="${count}"),
                ],
                # Translators: not url
                "requests": _("requests"),
                "close": _("close"),
                "makeRequest": _("Make request"),
                "writingRequestTo": _("You are writing a request to"),
                "toMultiPublicBodies": _("To: {count} public bodies").format(
                    count="${count}"
                ),
                "selectPublicBodies": _("Select public bodies"),
                "continue": _("continue"),
                "selectAll": [_("select one"), _("select all")],
                "selectingAll": _("Selecting all public bodies, please wait..."),
                "name": _("Name"),
                "jurisdictionPlural": [
                    _("Jurisdiction"),
                    _("Jurisdictions"),
                ],
                "topicPlural": [
                    _("Topic"),
                    _("Topics"),
                ],
                "classificationPlural": [
                    _("Classification"),
                    _("Classifications"),
                ],
                "containingGeoregionsPlural": [
                    _("Part of administrative region"),
                    _("Part of administrative regions"),
                ],
                "administrativeUnitKind": _("Type of administrative unit"),
                "toPublicBody": _("To: {name}").format(name="${name}"),
                "change": _("Change"),
                "searchPlaceholder": _("Search..."),
                "clearSearchResults": _("clear search"),
                "clearSelection": _("clear selection"),
                "reallyClearSelection": _(
                    "Are you sure you want to discard your current selection?"
                ),
                "loadMore": _("load more..."),
                "next": _("next"),
                "previous": _("previous"),
                "choosePublicBody": _("Choose public authority"),
                "checkSelection": _("Check selection"),
                "checkRequest": _("Check request"),
                "goNextStep": _("Go to next step"),
                "batchRequestDraftOnly": _(
                    "You have been allowed to make one project request to "
                    "these public bodies, but you do not have permission "
                    "to select your own."
                ),
                "subject": _("Subject"),
                "defaultLetterStart": _("Please send me the following information:"),
                "warnFullText": _(
                    "Watch out! You are requesting information across jurisdictions! "
                    "If you write the full text, we cannot customize it according to "
                    "applicable laws. Instead you have to write the text to be "
                    "jurisdiction agnostic."
                ),
                "replacePlaceholderMarker": _(
                    _("Please replace all placeholder values marked by “{}”.").format(
                        PLACEHOLDER_MARKER
                    )
                ),
                "resetFullText": _("Reset text to template version"),
                "savedFullTextChanges": _("Your previous customized text"),
                "saveAsDraft": _("Save as draft"),
                "reviewRequest": _("Review request"),
                "reviewTitle": _("Review your request and submit"),
                "reviewEdit": _("Edit"),
                "reviewFrom": _("From"),
                "reviewTo": _("To"),
                "reviewPublicbodies": _("public bodies"),
                "reviewSpelling": _("Please use proper spelling."),
                "reviewPoliteness": _("Please stay polite."),
                "submitRequest": _("Submit request"),
                "greeting": _("Dear Sir or Madam"),
                "kindRegards": _("Kind regards"),
                "yourFirstName": _("Your first name"),
                "yourLastName": _("Your last name"),
                "yourEmail": _("Your email address"),
                "yourAddress": _("Your postal address"),
                "giveName": _("Please fill out your name below"),
                "similarExist": _(
                    "Please make sure the information is not already requested or public"
                ),
                "similarRequests": _("Similar requests"),
                "moreSimilarRequests": _("Search for more similar requests"),
                "relevantResources": _("Relevant resources"),
                "officialWebsite": _("Official website: "),
                "noSubject": _("Please add a subject."),
                "noBody": _("Please describe the information you want to request!"),
                "dontAddClosing": _(
                    "Do not add a closing, it is added automatically at the end of the letter."
                ),
                "dontAddGreeting": _(
                    "Do not add a greeting, it is added automatically at the start of the letter."
                ),
                "dontInsertName": _(
                    "Do not insert your name, we will add it automatically at the end of the letter."
                ),
                "enterMeaningfulSubject": _(
                    "Please enter a subject which describes the information you are requesting."
                ),
                "pleaseFollowAddressFormat": linebreaks(
                    _(
                        "Please enter an address in the following format:\n%(format)s",
                    )
                    % {"format": _("Street address,\nPost Code, City")}
                ),
                "includeProof": _("Attach a proof of identity"),
                "addMoreAuthorities": _("Add more authorities"),
            },
            "regex": {
                "greetings": [_("Dear Sir or Madam")],
                "closings": [_("Kind Regards")],
            },
            "fixtures": {
                "georegion_kind": [
                    [str(k), str(v)]
                    for k, v in GeoRegion.KIND_CHOICES
                    if k in settings.FROIDE_CONFIG.get("filter_georegion_kinds", [])
                ],
            },
            "draftId": self.object.id
            if hasattr(self, "object") and isinstance(self.object, RequestDraft)
            else None,
            "wasPost": self.request.method == "POST",
        }
        pb_ctx = get_widget_context()
        for key in pb_ctx:
            if key in ctx:
                ctx[key].update(pb_ctx[key])
            else:
                ctx[key] = pb_ctx[key]
        proof_form = self.get_proof_form()
        if proof_form:
            ctx["proof_config"] = proof_form.get_js_context()
        return ctx

    def get_form_config_initial(self):
        return {k: True for k in self.FORM_CONFIG_PARAMS if k in self.request.GET}

    def get_form_kwargs(self):
        kwargs = super(MakeRequestView, self).get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_user_initial(self):
        request = self.request
        initial_user_data = {}
        if "email" in request.GET:
            initial_user_data["user_email"] = request.GET["email"]
        if "first_name" in request.GET:
            initial_user_data["first_name"] = request.GET["first_name"]
        if "last_name" in request.GET:
            initial_user_data["last_name"] = request.GET["last_name"]
        return initial_user_data

    def get_user_form(self):
        if self.request.user.is_authenticated:
            form_klass = AddressForm
            kwargs = {
                "initial": {"address": self.request.user.address},
                "request": self.request,
            }
        else:
            form_klass = NewUserForm
            kwargs = {"initial": self.get_user_initial(), "request": self.request}
        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return form_klass(**kwargs)

    def get_publicbody_form_kwargs(self):
        kwargs = {}
        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                }
            )
        return kwargs

    def get_publicbodies(self):
        if self.request.method == "POST":
            # on POST public bodies need to come from POST vars
            if self.has_prepared_publicbodies():
                # prepared draft with fixed public bodies
                return self.draft.publicbodies.all()
            self._publicbodies = []
        if hasattr(self, "_publicbodies"):
            return self._publicbodies
        pbs = self.get_publicbodies_from_context()
        self._publicbodies = pbs
        return pbs

    def has_prepared_publicbodies(self):
        return (
            not self.can_create_batch() and self.draft and self.draft.is_multi_request
        )

    def get_publicbodies_from_context(self):
        publicbody_ids = self.kwargs.get(
            "publicbody_ids", self.request.GET.get("publicbody")
        )
        publicbody_slug = self.kwargs.get("publicbody_slug")
        publicbodies = []
        if publicbody_ids:
            publicbody_ids = publicbody_ids.split("+")
            try:
                publicbodies = PublicBody.objects.filter(pk__in=publicbody_ids)
            except ValueError:
                raise Http404 from None
            if len(publicbody_ids) != len(publicbodies):
                raise Http404
            if len(publicbody_ids) > 1 and not self.can_create_batch():
                raise Http404
        elif publicbody_slug is not None:
            publicbody = get_object_or_404(PublicBody, slug=publicbody_slug)
            if not publicbody.email:
                raise Http404
            publicbodies = [publicbody]
        return publicbodies

    def can_create_batch(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.has_perm("foirequest.create_batch")

    def get_publicbody_form_class(self):
        if self.can_create_batch():
            return MultiplePublicBodyForm
        return PublicBodyForm

    def get_publicbody_form(self):
        publicbodies = self.get_publicbodies()
        if not publicbodies:
            form_class = self.get_publicbody_form_class()
            return form_class(**self.get_publicbody_form_kwargs())
        return FakePublicBodyForm(publicbodies)

    def get_proof_form(self):
        if not self.request.user.is_authenticated:
            # Can't send proof if not logged in
            return None
        if self.request.method in ("POST", "PUT"):
            return ProofMessageForm(
                self.request.POST, self.request.FILES, user=self.request.user
            )
        return ProofMessageForm(user=self.request.user)

    def csrf_valid(self):
        """
        This runs a replaceable csrf view middleware
        on the request and checks if something other than
        None is returned, indicating csrf failure
        """

        @csrf_protect
        def fake_view(request):
            return None

        return not bool(fake_view(self.request))

    def post(self, request, *args, **kwargs):
        error = False
        request = self.request

        self.csrf_failed = False
        if not self.csrf_valid():
            self.csrf_failed = True
            error = True

        request_form = self.get_form()

        if not request.POST.get("save_draft", ""):
            throttle_message = check_throttle(request.user, FoiRequest)
            if throttle_message:
                request_form.add_error(None, throttle_message)

        if not request_form.is_valid():
            error = True

        self.draft = request_form.get_draft()
        publicbody_form = self.get_publicbody_form()

        if not publicbody_form.is_valid():
            error = True

        if self.has_prepared_publicbodies() and self.draft.project:
            request_form.add_error(None, _("Draft cannot be used again."))
            error = True

        if request_form.is_valid() and request.user.is_authenticated:
            if request.POST.get("save_draft", ""):
                return self.save_draft(request_form, publicbody_form)
            if request.user.is_blocked:
                messages.add_message(
                    self.request,
                    messages.WARNING,
                    _("Your account cannot send requests."),
                )
                return self.save_draft(request_form, publicbody_form)

        user_form = self.get_user_form()
        if not user_form.is_valid():
            error = True

        form_kwargs = {
            "request_form": request_form,
            "user_form": user_form,
            "publicbody_form": publicbody_form,
            "proof_form": self.get_proof_form(),
        }

        if not error:
            return self.form_valid(**form_kwargs)
        return self.form_invalid(**form_kwargs)

    def save_draft(self, request_form, publicbody_form):
        publicbodies = publicbody_form.get_publicbodies()

        service = SaveDraftService(
            {"publicbodies": publicbodies, "request_form": request_form}
        )
        service.execute(self.request)
        messages.add_message(
            self.request,
            messages.INFO,
            _("Your request has been saved to your drafts."),
        )

        return redirect("account-drafts")

    def form_invalid(self, **form_kwargs):
        if not self.csrf_failed:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "There were errors in your form submission. "
                    "Please review and submit again."
                ),
            )
        else:
            messages.add_message(
                self.request, messages.INFO, _("Please confirm your form submission.")
            )
        return self.render_to_response(self.get_context_data(**form_kwargs), status=400)

    def form_valid(
        self, request_form=None, publicbody_form=None, user_form=None, proof_form=None
    ):
        user = self.request.user
        data = dict(request_form.cleaned_data)
        data["user"] = user
        data["publicbodies"] = publicbody_form.get_publicbodies()

        if not user.is_authenticated:
            data.update(user_form.cleaned_data)
        elif user_form is not None:
            data["address"] = user_form.cleaned_data.get("address")
            user_form.save(user=user)
        if proof_form and proof_form.is_valid():
            data["proof"] = proof_form.save()

        service = CreateRequestService(data)
        foi_object = service.execute(self.request)

        return self.make_redirect(
            request_form, foi_object, email=data.get("user_email")
        )

    def make_redirect(self, request_form, foi_object, email=None):
        user = self.request.user
        special_redirect = request_form.cleaned_data["redirect_url"]

        if user.is_authenticated:
            params = {}
            if isinstance(foi_object, FoiRequest):
                params["request"] = str(foi_object.pk)
            else:
                params["project"] = str(foi_object.pk)

            if special_redirect:
                special_redirect = update_query_params(special_redirect, params)
                return redirect(special_redirect)

            req_url = "%s?%s" % (reverse("foirequest-request_sent"), urlencode(params))
            return redirect(req_url)

        return redirect(get_new_account_url(foi_object, email=email))

    def get_config(self, form):
        config = {}
        if self.request.method in ("POST", "PUT"):

            def get_from_form(key):
                return form.cleaned_data.get(key, False)

            source_func = get_from_form
        else:

            def get_from_query(key):
                return key in self.request.GET

            source_func = get_from_query

        for key in self.FORM_CONFIG_PARAMS:
            config[key] = source_func(key)
        return config

    def get_context_data(self, **kwargs):
        if "request_form" not in kwargs:
            kwargs["request_form"] = self.get_form()

        if "publicbody_form" not in kwargs:
            kwargs["publicbody_form"] = self.get_publicbody_form()

        if "proof_form" not in kwargs:
            kwargs["proof_form"] = self.get_proof_form()

        publicbodies_json = "[]"
        publicbodies = self.get_publicbodies()
        if not publicbodies:
            publicbodies = kwargs["publicbody_form"].get_publicbodies()
        if publicbodies:
            publicbodies_json = json.dumps(
                PublicBodyListSerializer(
                    publicbodies, context={"request": self.request}, many=True
                ).data["objects"]
            )

        if "user_form" not in kwargs:
            kwargs["user_form"] = self.get_user_form()

        config = self.get_config(kwargs["request_form"])

        is_multi = False
        if kwargs["publicbody_form"] and kwargs["publicbody_form"].is_multi:
            is_multi = True
        if publicbodies and len(publicbodies) > 1:
            is_multi = True
        if self.request.GET.get("single") is not None:
            is_multi = False

        if self.request.method == "POST" or publicbodies:  # or is_multi:
            campaigns = None
        else:
            campaigns = Campaign.objects.get_active()

        kwargs.update(
            {
                "publicbodies": publicbodies,
                "publicbodies_json": publicbodies_json,
                "multi_request": is_multi,
                "beta_ui": self.request.GET.get("beta") is not None,
                "config": config,
                "campaigns": campaigns,
                "js_config": json.dumps(self.get_js_context()),
                "public_body_search": self.request.GET.get("topic", ""),
            }
        )
        return kwargs


class DraftRequestView(MakeRequestView, DetailView):
    def get_queryset(self):
        return get_read_queryset(RequestDraft.objects.all(), self.request)

    def get_config(self, form):
        config = {}
        for key in self.FORM_CONFIG_PARAMS:
            if key in self.object.flags:
                config[key] = self.object.flags[key]
        return config

    def get_initial(self):
        return self.object.get_initial()

    def get_publicbodies_from_context(self):
        return self.object.publicbodies.all()


def get_new_account_url(foi_object, email=None):
    url = reverse("account-new")
    d = {"title": foi_object.title.encode("utf-8")}
    if email is not None:
        d["email"] = email.encode("utf-8")
    query = urlencode(d)
    return "%s?%s" % (url, query)


class RequestSentView(LoginRequiredMixin, TemplateView):
    template_name = "foirequest/sent.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["foirequest"] = self.get_foirequest()
        context["foiproject"] = self.get_foiproject()
        foi_obj = context["foirequest"] or context["foiproject"]
        if foi_obj:
            context["is_public"] = foi_obj.is_public
            context["url"] = foi_obj.get_absolute_url()
            context["share_url"] = foi_obj.get_absolute_domain_url()
        return context

    def get_foirequest(self):
        request_pk = self.request.GET.get("request")
        if request_pk:
            try:
                return FoiRequest.objects.get(user=self.request.user, pk=request_pk)
            except FoiRequest.DoesNotExist:
                pass
        return None

    def get_foiproject(self):
        project_pk = self.request.GET.get("project")
        if project_pk:
            try:
                return FoiProject.objects.get(user=self.request.user, pk=project_pk)
            except FoiProject.DoesNotExist:
                pass
        return None
