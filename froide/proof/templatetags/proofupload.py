from django import template

from ..forms import ProofForm
from ..models import Proof

register = template.Library()


@register.simple_tag
def get_proof_form():
    form = ProofForm()
    return form


@register.simple_tag(takes_context=True)
def get_user_proofs(context):
    request = context["request"]
    proofs = Proof.objects.filter(user=request.user)
    return proofs
