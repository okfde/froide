import json
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import UpdateView

from froide.account.forms import AddressForm, NewUserForm
from froide.foirequest.forms.project import AssignProjectForm
from froide.foirequest.forms.request import RedactDescriptionForm
from froide.helper.auth import can_manage_object
from froide.helper.utils import get_redirect, is_ajax, render_400, render_403
from froide.team.views import AssignTeamView

from ..auth import (
    can_mark_not_foi,
    can_moderate_foirequest,
    can_write_foirequest,
    check_foirequest_upload_code,
    get_read_foirequest_queryset,
)
from ..decorators import allow_write_foirequest, allow_write_or_moderate_pii_foirequest
from ..forms import (
    ApplyModerationForm,
    ConcreteLawForm,
    ExtendDeadlineForm,
    FoiRequestStatusForm,
    MakePublicBodySuggestionForm,
    PublicBodySuggestionsForm,
    PublicBodyUploader,
    TagFoiRequestForm,
)
from ..hooks import registry
from ..models import FoiEvent, FoiRequest
from ..services import ActivatePendingRequestService, CreateSameAsRequestService
from ..utils import check_throttle, get_foi_mail_domains
from .make_request import get_new_account_url
from .request import show_foirequest


@require_POST
@allow_write_foirequest
def set_public_body(request, foirequest):
    form = PublicBodySuggestionsForm(request.POST, foirequest=foirequest)
    if not form.is_valid():
        return render_400(request)

    throttle_message = check_throttle(request.user, FoiRequest)
    if throttle_message:
        message = "\n".join(throttle_message.messages)
        messages.add_message(request, messages.ERROR, message)
        return render_400(request)

    form.save(user=request.user)

    messages.add_message(
        request,
        messages.SUCCESS,
        _("Request was sent to: {name}.").format(name=foirequest.public_body.name),
    )
    return redirect(foirequest)


@require_POST
def suggest_public_body(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not foirequest.needs_public_body():
        return render_400(request)
    form = MakePublicBodySuggestionForm(request.POST)
    if form.is_valid():
        publicbody = form.publicbody_object
        user = None
        if request.user.is_authenticated:
            user = request.user
        response = foirequest.suggest_public_body(
            publicbody, form.cleaned_data["reason"], user
        )
        if response:
            messages.add_message(
                request,
                messages.SUCCESS,
                _("Your Public Body suggestion has been added."),
            )
        else:
            messages.add_message(
                request,
                messages.WARNING,
                _("This Public Body has already been suggested."),
            )
        return redirect(foirequest)

    messages.add_message(
        request, messages.ERROR, _("You need to specify a Public Body!")
    )
    return render_400(request)


@require_POST
def set_status(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not can_write_foirequest(foirequest, request):
        if not can_moderate_foirequest(foirequest, request):
            return render_403(request)
        else:
            if not foirequest.moderate_classification():
                return render_403(request)

    form = FoiRequestStatusForm(request.POST, foirequest=foirequest)
    if form.is_valid():
        form.save(user=request.user)
        messages.add_message(
            request, messages.SUCCESS, _("Status of request has been updated.")
        )
        if form.cleaned_data["resolution"] in ("user_withdrew", "user_withdrew_costs"):
            request.session["show_withdrawal_popup"] = foirequest.id
        response = registry.run_hook(
            "post_status_set",
            request,
            user=request.user,
            data={"foirequest": foirequest, "form": form},
        )
        if response is not None:
            return response
    else:
        messages.add_message(
            request, messages.ERROR, _("Invalid value for form submission!")
        )
        return show_foirequest(
            request, foirequest, context={"status_form": form}, status=400
        )
    return redirect(foirequest.get_absolute_url() + "#-")


@require_POST
@allow_write_foirequest
def make_public(request, foirequest):
    if not foirequest.is_foi:
        return render_400(request)
    foirequest.make_public(user=request.user)
    return redirect(foirequest)


@require_POST
@allow_write_foirequest
def set_law(request, foirequest):
    form = ConcreteLawForm(request.POST, foirequest=foirequest)
    if not form.is_valid():
        return render_400(request)
    form.save(user=request.user)
    messages.add_message(
        request, messages.SUCCESS, _("A concrete law has been set for this request.")
    )
    return redirect(foirequest)


@require_POST
@allow_write_foirequest
def set_tags(request, foirequest):
    form = TagFoiRequestForm(request.POST)
    if form.is_valid():
        form.save(foirequest)
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.SET_TAGS,
            foirequest,
            user=request.user,
            tags=str(form.cleaned_data["tags"]),
        )
        messages.add_message(
            request, messages.SUCCESS, _("Tags have been set for this request.")
        )
    return redirect(foirequest)


@require_POST
@allow_write_foirequest
def set_summary(request, foirequest):
    summary = request.POST.get("summary", None)
    if summary is None:
        return render_400(request)
    foirequest.summary = summary
    foirequest.save()
    FoiEvent.objects.create_event(
        FoiEvent.EVENTS.SET_SUMMARY, foirequest, user=request.user
    )
    messages.add_message(
        request, messages.SUCCESS, _("The outcome summary has been saved.")
    )
    return redirect(foirequest)


@require_POST
@login_required
def apply_moderation(request, slug):
    foirequest = get_object_or_404(get_read_foirequest_queryset(request), slug=slug)

    if not can_mark_not_foi(foirequest, request):
        return render_403(request)

    form = ApplyModerationForm(
        data=request.POST, foirequest=foirequest, request=request
    )
    if form.is_valid():
        result_messages = form.save()
        result_str = " ".join([str(x) for x in result_messages])
        if is_ajax(request):
            return HttpResponse(result_str)
        messages.add_message(request, messages.SUCCESS, result_str)
    return redirect(foirequest)


@require_POST
def make_same_request(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not foirequest.not_publishable:
        return redirect(foirequest)
    if foirequest.same_as is not None:
        foirequest = foirequest.same_as

    if not request.user.is_authenticated:
        new_user_form = NewUserForm(request.POST, request=request)
        if not new_user_form.is_valid():
            return show_foirequest(
                request,
                foirequest,
                context={"new_user_form": new_user_form},
                status=400,
            )
    else:
        user = request.user
        if foirequest.user == user:
            return render_400(request)
        same_requests = FoiRequest.objects.filter(
            user=user, same_as=foirequest
        ).exists()
        if same_requests:
            messages.add_message(
                request, messages.ERROR, _("You already made an identical request")
            )
            return render_400(request)
        address_form = AddressForm(request.POST, request=request)
        if address_form.is_valid():
            address_form.save(user)

    throttle_message = check_throttle(request.user, FoiRequest)
    if throttle_message:
        messages.add_message(request, messages.ERROR, "\n".join(throttle_message))
        return render_400(request)

    body = foirequest.description
    if foirequest.status_is_final():
        body = "{}\n\n{}".format(
            foirequest.description,
            _(
                "Please see this request on %(site_name)s where you granted access to this information: %(url)s"
            )
            % {
                "url": foirequest.get_absolute_domain_short_url(),
                "site_name": settings.SITE_NAME,
            },
        )

    data = {
        "user": request.user,
        "publicbodies": [foirequest.public_body],
        "subject": foirequest.title,
        "body": body,
        "public": foirequest.public,
        "original_foirequest": foirequest,
    }
    if request.POST.get("redirect_url"):
        data["redirect_url"] = request.POST["redirect_url"]
    if request.POST.get("reference"):
        data["reference"] = request.POST["reference"]

    if not request.user.is_authenticated:
        data.update(new_user_form.cleaned_data)

    service = CreateSameAsRequestService(data)
    new_foirequest = service.execute(request)

    count = FoiRequest.objects.filter(same_as=foirequest).count()
    FoiRequest.objects.filter(id=foirequest.id).update(same_as_count=count)

    if request.user.is_active:
        messages.add_message(
            request,
            messages.SUCCESS,
            _(
                "You successfully requested this document! "
                "Your request is displayed below."
            ),
        )
        return redirect(new_foirequest)
    else:
        messages.add_message(
            request,
            messages.INFO,
            _(
                "Please check your inbox for mail from us to "
                "confirm your mail address."
            ),
        )
        # user cannot access the request yet!
        return redirect(get_new_account_url(new_foirequest))


@require_POST
@allow_write_foirequest
def extend_deadline(request, foirequest):
    form = ExtendDeadlineForm(request.POST)
    if form.is_valid():
        form.save(foirequest)
        messages.add_message(request, messages.INFO, _("Deadline has been extended."))
        FoiEvent.objects.create_event(
            "deadline_extended", foirequest, user=request.user
        )
        return redirect(foirequest)
    return render_400(request)


class SetTeamView(AssignTeamView):
    model = FoiRequest


class SetProjectView(UpdateView):
    model = FoiRequest
    form_class = AssignProjectForm
    template_name = "foirequest/foiproject_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        if not can_manage_object(obj, self.request):
            raise Http404
        return obj

    def get(self, request, *args, **kwargs):
        return redirect(self.get_object())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


@require_POST
@allow_write_foirequest
def confirm_request(request, foirequest):
    if foirequest.status != FoiRequest.STATUS.AWAITING_USER_CONFIRMATION:
        return render_400(request)

    req_service = ActivatePendingRequestService({"foirequest": foirequest})
    foirequest = req_service.process(request=request)
    if not foirequest:
        return render_400(request)

    return redirect(foirequest)


@require_POST
@allow_write_foirequest
def delete_request(request, foirequest):
    if foirequest.status != FoiRequest.STATUS.AWAITING_USER_CONFIRMATION:
        return render_400(request)

    if foirequest.user != request.user:
        return render_400(request)

    foirequest.delete()

    return get_redirect(request)


def publicbody_upload(request, obj_id, code):
    from froide.upload.forms import get_uppy_i18n

    foirequest = get_object_or_404(FoiRequest, id=obj_id, closed=False)
    if not check_foirequest_upload_code(foirequest, code):
        return render_403(request)
    # Not for authenticated users
    if request.user.is_authenticated:
        # Don't leak slug, so go to short url
        return redirect(foirequest.get_absolute_short_url())

    pb_upload_auth = request.session.get("pb_upload_auth")
    if pb_upload_auth != foirequest.secret_address:
        email_domain = get_foi_mail_domains()[0]
        if request.method == "POST":
            email_prefix = request.POST.get("email_prefix", "")
            email_prefix = email_prefix.replace("@{}".format(email_domain), "")
            email = "{}@{}".format(email_prefix, email_domain)
            if email == foirequest.secret_address:
                request.session["pb_upload_auth"] = email
                return redirect(request.get_full_path())
            else:
                messages.add_message(
                    request,
                    messages.ERROR,
                    _("The given email address is not correct for this request."),
                )

        return render(
            request,
            "foirequest/publicbody_upload.html",
            {
                "authenticated": False,
                "email_domain": get_foi_mail_domains()[0],
                "foirequest": foirequest,
            },
        )

    if request.method == "POST":
        token = request.session.get("upload_auth")
        if not token:
            messages.add_message(
                request,
                messages.ERROR,
                _(
                    "A session error occurred while authenticating your "
                    "uploads. Please contact administrators."
                ),
            )
            return redirect(request.get_full_path())
        uploader = PublicBodyUploader(foirequest, token)
        upload_list = request.POST.getlist("upload")
        att_count = uploader.create_upload_message(upload_list)

        messages.add_message(
            request,
            messages.SUCCESS,
            _("%s files were uploaded successfully. Thank you!") % att_count,
        )
        return redirect(request.get_full_path())

    if "upload_auth" not in request.session:
        request.session["upload_auth"] = str(uuid.uuid4())

    config = json.dumps(
        {
            "settings": {
                "tusChunkSize": settings.DATA_UPLOAD_MAX_MEMORY_SIZE - (500 * 1024)
            },
            "i18n": {
                "uppy": get_uppy_i18n(),
                "createResponse": _("Create response now"),
                "sureCancel": _(
                    "You have not completed this process. "
                    "Are you sure you want to cancel?"
                ),
            },
            "url": {
                "tusEndpoint": reverse("api:upload-list"),
            },
        }
    )
    return render(
        request,
        "foirequest/publicbody_upload.html",
        {"authenticated": True, "foirequest": foirequest, "config": config},
    )


@require_POST
@allow_write_or_moderate_pii_foirequest
def redact_description(request, foirequest):
    form = RedactDescriptionForm(request.POST)
    if form.is_valid():
        form.save(request, foirequest)
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.DESCRIPTION_REDACTED,
            foirequest,
            user=request.user,
            **form.cleaned_data
        )
    return redirect(foirequest.get_absolute_url())
