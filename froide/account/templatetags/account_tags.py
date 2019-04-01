from django import template

from ..forms import NewUserForm, AddressForm
from ..menu import menu_registry

register = template.Library()


@register.simple_tag(takes_context=True)
def get_user_form(context, address_required=False):
    request = context['request']
    if request.user.is_authenticated:
        return AddressForm(
            initial={
                'address': request.user.address
            },
            address_required=address_required
        )
    else:
        return NewUserForm(address_required=address_required)


@register.simple_tag(takes_context=True)
def get_menu_items(context):
    return menu_registry.get_menu_items(context['request'])
