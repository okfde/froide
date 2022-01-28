from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt

from froide.foirequest.views.request import show_foirequest
from froide.foirequest.auth import get_read_foirequest_queryset
from froide.helper.utils import is_ajax

from .models import FoiRequestFollower
from .forms import FollowRequestForm
from .utils import get_context


@require_POST
def follow(request, pk):
    qs = get_read_foirequest_queryset(request)
    if request.user.is_authenticated:
        qs = qs.exclude(user=request.user)
    foirequest = get_object_or_404(qs, pk=pk)
    form = FollowRequestForm(request.POST, foirequest=foirequest, request=request)
    if form.is_valid():
        followed = form.save()
        if is_ajax(request):
            return render(
                request,
                "foirequestfollower/show.html",
                {
                    "count": foirequest.follow_count(),
                    "object": foirequest,
                    "email_followed": not request.user.is_authenticated,
                },
            )
        if request.user.is_authenticated:
            if followed:
                messages.add_message(
                    request, messages.SUCCESS, _("You are now following this request.")
                )
            else:
                messages.add_message(
                    request,
                    messages.INFO,
                    _("You are not following this request anymore."),
                )
        else:
            messages.add_message(
                request,
                messages.SUCCESS,
                _(
                    "Check your emails and click the confirmation link in order to follow this request."
                ),
            )
        return redirect(foirequest)

    if is_ajax(request):
        error_string = " ".join(" ".join(v) for k, v in form.errors.items())
        return JsonResponse({"errors": error_string})
    return show_foirequest(
        request, foirequest, context={"followform": form}, status=400
    )


@xframe_options_exempt
def embed_follow(request, pk):
    qs = get_read_foirequest_queryset(request)
    foirequest = get_object_or_404(qs, pk=pk)
    return render(
        request,
        "foirequestfollower/embed_form.html",
        get_context(foirequest, request, embed=True),
    )


def confirm_follow(request, follow_id, check):
    follower = get_object_or_404(FoiRequestFollower, id=int(follow_id))
    if follower.check_and_follow(check):
        messages.add_message(
            request,
            messages.SUCCESS,
            _("You will now receive email notifications for this request!"),
        )
    else:
        messages.add_message(
            request,
            messages.ERROR,
            _("There was something wrong with your link. Perhaps try again."),
        )
    return redirect(follower.request)


def unfollow_by_link(request, follow_id, check):
    try:
        follower = FoiRequestFollower.objects.get(id=int(follow_id))
    except FoiRequestFollower.DoesNotExist:
        messages.add_message(
            request,
            messages.INFO,
            _("This follow subscription does not exist anymore."),
        )
        return redirect("/")
    if follower.check_and_unfollow(check):
        messages.add_message(
            request, messages.INFO, _("You are not following this request anymore.")
        )
    else:
        messages.add_message(
            request,
            messages.ERROR,
            _("There was something wrong with your link. Perhaps try again."),
        )
    return redirect(follower.request)
