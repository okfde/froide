from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from .forms import ProofSettingsForm
from .models import Proof


@require_POST
@login_required
@sensitive_post_parameters()
def add_proof(request):
    form = ProofSettingsForm(data=request.POST, files=request.FILES)
    if form.is_valid():
        form.save(request)
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Proof added successfully."),
        )
    else:
        messages.add_message(
            request,
            messages.ERROR,
            _("There was a problem."),
        )
    return redirect(reverse("account-settings") + "#proofs")


@require_POST
@login_required
def delete_proof(request, proof_id):
    qs = Proof.objects.filter(user=request.user)
    proof = get_object_or_404(qs, id=proof_id)
    proof.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Proof successfully removed."),
    )
    return redirect(reverse("account-settings") + "#proofs")
