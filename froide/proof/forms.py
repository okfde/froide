from typing import Optional

from django import forms
from django.conf import settings
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from froide.helper.content_urls import get_content_url
from froide.helper.form_utils import JSONMixin
from froide.helper.widgets import (
    BootstrapCheckboxInput,
    BootstrapSelect,
    BootstrapTextInput,
)

from .models import Proof, ProofAttachment, TemporaryProof
from .widgets import ProofImageWidget, get_widget_context


def get_proof_choice_field(user, initial=None):
    proof_choices = Proof.objects.filter(user=user)
    if proof_choices:
        return forms.ModelChoiceField(
            label=_("Proof"),
            help_text=_(
                "If you want to send one of your proofs of identity, choose it here."
            ),
            queryset=proof_choices,
            required=False,
            initial=initial,
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


class ProofMessageForm(JSONMixin, ProofSettingsForm):
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
        self.user = user
        if user.is_authenticated:
            proof_choice = get_proof_choice_field(
                user, initial=self.initial.get("proof")
            )
            if proof_choice:
                self.fields["proof"] = proof_choice
        self.fields["proof_store"].help_text = format_html(
            _(
                "By checking this box, I agree that the image file I have selected "
                "and redacted may be stored by {site_name} in my user account, so "
                "that I can use it as proof of identity in future requests if "
                "necessary. I certify that I am the owner of this document. I "
                "understand that my consent is voluntary and that I can revoke it "
                "at any time with effect for the future. I have taken note of the "
                "information on the recommended redactions and the "
                '<a href="{url_privacy}" target="_blank">data protection '
                "declaration</a>."
            ),
            site_name=settings.SITE_NAME,
            url_privacy=get_content_url("privacy"),
        )
        self.order_fields(self.field_order)

    def get_js_context(self):
        return get_widget_context()

    def save_proof(self, name):
        proof = Proof(user=self.user, name=name)
        proof.save_with_file(self.cleaned_data["proof_image"])
        return proof

    def save(self) -> Optional[ProofAttachment]:
        if self.cleaned_data["proof_image"]:
            name = self.cleaned_data["proof_name"]
            if not name:
                name = str(_("Proof of identity"))
            if self.user.is_authenticated and self.cleaned_data["proof_store"]:
                return self.save_proof(name)
            return TemporaryProof(name, self.cleaned_data["proof_image"])

        if self.cleaned_data.get("proof"):
            return self.cleaned_data["proof"]
        return None


def handle_proof_form(request) -> Optional[ProofAttachment]:
    form = ProofMessageForm(request.POST, request.FILES, user=request.user)
    if form.is_valid():
        return form.save()
    return None
