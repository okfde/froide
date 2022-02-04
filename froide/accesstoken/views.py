from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from froide.helper.utils import get_redirect, render_403

from .forms import ResetTokenForm


@require_POST
def reset_token(request):
    if not request.user.is_authenticated:
        return render_403(request)

    form = ResetTokenForm(data=request.POST, user=request.user)
    if form.is_valid():
        message = form.save()
        messages.add_message(request, messages.SUCCESS, message)
    else:
        messages.add_message(request, messages.ERROR, _("Failed to reset token."))

    return get_redirect(request)
