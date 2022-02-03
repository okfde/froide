from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from froide.helper.utils import render_403

from ..models import RequestDraft


@require_POST
def delete_draft(request):
    if not request.user.is_authenticated:
        return render_403(request)

    pk = request.POST.get("draft_id")
    draft = get_object_or_404(RequestDraft, pk=pk, user=request.user)
    draft.delete()
    messages.add_message(request, messages.INFO, _("The draft has been deleted."))

    return redirect("account-drafts")


def claim_draft(request, token):
    if not request.user.is_authenticated:
        # This should lead to a login page with next set to drafts
        return redirect("account-drafts")
    try:
        draft = RequestDraft.objects.get(token=token, user=None)
    except RequestDraft.DoesNotExist:
        return redirect("account-drafts")
    draft.token = None
    draft.user = request.user
    draft.save()
    messages.add_message(
        request,
        messages.INFO,
        _(
            "Please check the request you wanted to make and send it when you are ready."
        ),
    )
    return redirect(draft)
