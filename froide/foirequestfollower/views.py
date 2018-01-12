from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages

from froide.foirequest.models import FoiRequest
from froide.foirequest.views import show

from .models import FoiRequestFollower
from .forms import FollowRequestForm


@require_POST
def follow(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    form = FollowRequestForm(foirequest, request, request.POST)
    if form.is_valid():
        followed = form.save()
        if request.is_ajax():
            return JsonResponse({'followed': followed})
        if request.user.is_authenticated:
            if followed:
                messages.add_message(request, messages.SUCCESS,
                        _("You are now following this request."))
            else:
                messages.add_message(request, messages.INFO,
                        _("You are not following this request anymore."))
        else:
            if followed is None:
                messages.add_message(request, messages.INFO,
                        _("You have not yet confirmed that you want to follow this request. Click the link in the mail that was sent to you."))
            elif followed:
                messages.add_message(request, messages.SUCCESS,
                        _("Check your emails and click the confirmation link in order to follow this request."))
            else:
                messages.add_message(request, messages.INFO,
                        _("You are following this request. If you want to unfollow it, click the unfollow link in the emails you received."))
        return redirect(foirequest)

    if request.is_ajax():
        return JsonResponse({'errors': form.errors})
    return show(request, slug, context={"followform": form}, status=400)


def confirm_follow(request, follow_id, check):
    get_object_or_404(FoiRequestFollower, id=int(follow_id))


def unfollow_by_link(request, follow_id, check):
    follower = get_object_or_404(FoiRequestFollower, id=int(follow_id))
    if follower.check_and_unfollow(check):
        messages.add_message(request, messages.INFO,
            _("You are not following this request anymore."))
    else:
        messages.add_message(request, messages.ERROR,
            _("There was something wrong with your link. Perhaps try again."))
    return redirect(follower.request)
