from django import template

from ..forms import NewUserForm
from ..menu import menu_registry

register = template.Library()


@register.simple_tag
def get_new_user_form():
    return NewUserForm()


@register.simple_tag(takes_context=True)
def get_menu_items(context):
    return menu_registry.get_menu_items(context['request'])
