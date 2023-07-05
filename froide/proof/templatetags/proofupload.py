from django import template

from ..forms import ProofMessageForm, ProofSettingsForm
from ..models import Proof

register = template.Library()


@register.simple_tag
def get_proof_settings_form():
    form = ProofSettingsForm()
    return form


@register.simple_tag(takes_context=True)
def get_proof_message_form(context):
    form = ProofMessageForm(user=context["request"].user)
    return form


@register.simple_tag(takes_context=True)
def get_user_proofs(context):
    request = context["request"]
    proofs = Proof.objects.filter(user=request.user)
    return proofs
