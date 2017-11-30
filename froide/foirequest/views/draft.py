from __future__ import unicode_literals

from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages

from froide.helper.utils import render_403

from ..models import RequestDraft


@require_POST
def delete_draft(request):
    if not request.user.is_authenticated:
        return render_403(request)

    pk = request.POST.get('draft_id')
    draft = get_object_or_404(RequestDraft, pk=pk, user=request.user)
    draft.delete()
    messages.add_message(request, messages.INFO,
        _('The draft has been deleted.'))

    return redirect('account-drafts')
