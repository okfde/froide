from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import permission_required
from django.contrib import messages

from froide.foirequest.models import FoiMessage
from froide.helper.utils import render_403

from .utils import run_guidance


@require_POST
@permission_required('guide.can_run_guidance')
def rerun_rules(request, message_id):
    if not request.user.is_staff:
        return render_403(request)

    message = get_object_or_404(FoiMessage, id=message_id)
    notify = False

    if request.POST.get('notify'):
        notify = True

    run_guidance(message, active_only=False, notify=notify)

    messages.add_message(
        request, messages.SUCCESS,
        _('Guidance refreshed for message.')
    )

    return redirect(message)
