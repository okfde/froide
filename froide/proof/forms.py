from typing import Optional

from django import forms
from django.utils.translation import gettext_lazy as _

from froide.helper.widgets import (
    BootstrapCheckboxInput,
    BootstrapSelect,
    BootstrapTextInput,
)

from .models import Proof, ProofAttachment, TemporaryProof
from .widgets import ProofImageWidget


def get_proof_choice_field(user):
    proof_choices = Proof.objects.filter(user=user)
    if proof_choices:
        return forms.ModelChoiceField(
            label=_("Proof"),
            help_text=_(
                "If you want to send one of your proofs of identity, choose it here."
            ),
            queryset=proof_choices,
            required=False,
            widget=BootstrapSelect,
        )


class ProofSettingsForm(forms.Form):
    proof_name = forms.CharField(
        max_length=255,
        required=True,
        label=_("Name of Proof"),
        help_text=_("Label this proof, e.g. 'ID card' or 'Passport'."),
        widget=BootstrapTextInput,
    )
    proof_image = forms.ImageField(
        required=True, label=_("Select image of proof"), widget=ProofImageWidget
    )

    def save(self, request):
        proof = Proof(user=request.user, name=self.cleaned_data["proof_name"])
        proof.save_with_file(self.cleaned_data["proof_image"])
        return proof


class ProofMessageForm(ProofSettingsForm):
    proof_store = forms.BooleanField(
        required=False,
        label=_("Store this proof in your account for repeated use."),
        widget=BootstrapCheckboxInput,
    )
    field_order = ["proof", "proof_name", "proof_image", "proof_store"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proof_name"].required = False
        self.fields["proof_image"].required = False
        if user.is_authenticated:
            proof_choice = get_proof_choice_field(user)
            if proof_choice:
                self.fields["proof"] = proof_choice
        if not user.is_authenticated:
            del self.fields["proof_store"]

        self.order_fields(self.field_order)

    def save_proof(self, user, name):
        proof = Proof(user=user, name=name)
        proof.save_with_file(self.cleaned_data["proof_image"])
        return proof

    def save(self, user) -> Optional[ProofAttachment]:
        if self.cleaned_data["proof_image"]:
            name = self.cleaned_data["proof_name"]
            if not name:
                name = str(_("Proof of identity"))
            if user.is_authenticated and self.cleaned_data["proof_store"]:
                return self.save_proof(user, name)
            return TemporaryProof(name, self.cleaned_data["proof_image"])

        if self.cleaned_data.get("proof"):
            return self.cleaned_data["proof"]
        return None


def handle_proof_form(request) -> Optional[ProofAttachment]:
    form = ProofMessageForm(request.POST, request.FILES, user=request.user)
    if form.is_valid():
        return form.save(request.user)
    return None
