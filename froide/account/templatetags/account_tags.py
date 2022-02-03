import itertools

from django import template

from mfa.models import MFAKey

from ..forms import AddressForm, NewUserForm
from ..menu import menu_registry
from ..models import User

register = template.Library()


@register.simple_tag(takes_context=True)
def get_user_form(context, address_required=False):
    request = context["request"]
    if request.user.is_authenticated:
        return AddressForm(
            initial={"address": request.user.address}, address_required=address_required
        )
    else:
        return NewUserForm(address_required=address_required, request=request)


@register.simple_tag(takes_context=True)
def get_menu_items(context):
    return menu_registry.get_menu_items(context.get("request"))


@register.simple_tag(takes_context=True)
def get_mfa_keys(context):
    request = context["request"]
    user = request.user
    if not user.is_authenticated:
        if request.session.get("mfa_user"):
            user_pk = request.session["mfa_user"]["pk"]
            try:
                user = User.objects.get(id=user_pk)
            except User.DoesNotExist:
                return
        else:
            return

    keys = (
        MFAKey.objects.filter(user=user)
        .values("name", "method", "id")
        .order_by("method", "name")
    )
    by_method = {
        k: list(v) for k, v in itertools.groupby(keys, key=lambda x: x["method"])
    }
    return {"all": keys, "by_method": by_method}
