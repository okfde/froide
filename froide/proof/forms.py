from django import forms

from froide.helper.widgets import BootstrapTextInput

from .models import Proof
from .widgets import ProofImageWidget


class ProofForm(forms.Form):
    proof_name = forms.CharField(
        max_length=255,
        required=True,
        label="Name",
        help_text="Label this proof, e.g. 'ID card' or 'Passport'.",
        widget=BootstrapTextInput,
    )
    proof_image = forms.ImageField(
        required=True, label="Proof image", widget=ProofImageWidget
    )

    def save(self, request):
        proof = Proof(user=request.user, name=self.cleaned_data["proof_name"])
        proof.save_with_file(self.cleaned_data["proof_image"])
        return proof
