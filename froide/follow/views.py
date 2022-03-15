from typing import Optional

from django.contrib import messages
from django.http import Http404, HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_POST

from froide.follow.configuration import FollowConfiguration
from froide.helper.utils import is_ajax

from .models import follow_registry
from .utils import get_context


def get_configuration(slug: str) -> FollowConfiguration:
    if slug is None:
        from froide.foirequestfollower.configuration import (
            FoiRequestFollowConfiguration,
        )

        return FoiRequestFollowConfiguration()
    try:
        return follow_registry.get_by_slug(slug)
    except LookupError:
        raise Http404


@require_POST
def follow(request: HttpRequest, pk: int, conf_slug: Optional[str] = None):
    configuration = get_configuration(conf_slug)

    qs = configuration.get_content_object_queryset(request)
    content_object = get_object_or_404(qs, pk=pk)

    form_class = configuration.get_follow_form_class()

    form = form_class(
        request.POST,
        configuration=configuration,
        content_object=content_object,
        request=request,
    )
    if form.is_valid():
        followed = form.save()
        if is_ajax(request):
            return render(
                request,
                configuration.get_follow_templates(),
                get_context(
                    request,
                    content_object,
                    configuration,
                    email_followed=not request.user.is_authenticated,
                ),
            )
        if request.user.is_authenticated:
            if followed:
                messages.add_message(
                    request, messages.SUCCESS, configuration.get_follow_message()
                )
            else:
                messages.add_message(
                    request, messages.INFO, configuration.get_unfollow_message()
                )
        else:
            messages.add_message(
                request, messages.SUCCESS, configuration.get_confirm_email_message()
            )
        return redirect(content_object)

    error_string = " ".join(" ".join(v) for v in form.errors.values())
    if is_ajax(request):
        return JsonResponse({"errors": error_string})
    messages.add_message(request, messages.ERROR, error_string)
    return redirect(content_object)


@xframe_options_exempt
def embed_follow(request: HttpRequest, pk: int, conf_slug: Optional[str] = None):
    configuration = get_configuration(conf_slug)

    qs = configuration.get_content_object_queryset(request)
    content_object = get_object_or_404(qs, pk=pk)

    return render(
        request,
        "follow/embed_form.html",
        get_context(request, content_object, configuration, embed=True),
    )


def confirm_follow(
    request: HttpRequest, follow_id: int, check: str, conf_slug: Optional[str] = None
):
    configuration = get_configuration(conf_slug)

    follower = get_object_or_404(configuration.model, id=int(follow_id))
    if follower.check_and_follow(check):
        messages.add_message(
            request,
            messages.SUCCESS,
            configuration.get_follow_message(),
        )
    else:
        messages.add_message(
            request,
            messages.ERROR,
            _("There was something wrong with your link. Perhaps try again."),
        )
    return redirect(follower.content_object)


def unfollow_by_link(
    request: HttpRequest, follow_id: int, check: str, conf_slug: Optional[str] = None
):
    configuration = get_configuration(conf_slug)
    try:
        follower = configuration.model.objects.get(id=int(follow_id))
    except configuration.model.DoesNotExist:
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
    return redirect(follower.content_object)
