from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import permission_required
from django.contrib import messages

from froide.foirequest.models import FoiMessage
from froide.helper.utils import render_403

from .utils import apply_rules


@require_POST
@permission_required('guide.can_run_guidance')
def rerun_rules(request, message_id):
    if not request.user.is_staff:
        return render_403(request)

    message = get_object_or_404(FoiMessage, id=message_id)
    new_guidances = apply_rules(message)

    # Delete all guidances that were there before
    # but are not returned
    message.guidance_set.all().exclude(
        id__in=[n.id for n in new_guidances]
    ).delete()
    messages.add_message(
        request, messages.SUCCESS,
        _('Guidance refreshed for message.')
    )

    return redirect(message)
