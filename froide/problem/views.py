from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.contrib import messages

from froide.foirequest.models import FoiMessage

from froide.helper.utils import render_403

from .forms import ProblemReportForm


@require_POST
def report_problem(request, message_pk):
    message = get_object_or_404(FoiMessage, pk=message_pk)
    if not request.user.is_authenticated:
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
