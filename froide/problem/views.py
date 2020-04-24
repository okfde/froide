from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.contrib import messages

from froide.foirequest.models import FoiMessage
from froide.foirequest.auth import can_write_foirequest

from froide.helper.utils import render_403

from .forms import ProblemReportForm


@require_POST
def report_problem(request, message_pk):
    message = get_object_or_404(FoiMessage, pk=message_pk)
    foirequest = message.request
    if not can_write_foirequest(foirequest, request):
        return render_403(request)

    form = ProblemReportForm(
        data=request.POST, user=request.user,
        message=message
    )
    if form.is_valid():
        form.save()
    else:
        messages.add_message(
            request, messages.ERROR,
            _('Your report could not be created.')
        )
    return redirect(message)
