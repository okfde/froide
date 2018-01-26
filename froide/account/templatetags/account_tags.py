from django import template

from ..forms import NewUserForm
from ..menu import menu_registry

register = template.Library()


@register.simple_tag(takes_context=True)
def get_new_user_form(context, var_name):
    form = NewUserForm()
    context[var_name] = form
    return ""


@register.simple_tag(takes_context=True)
def get_menu_items(context, var_name):
    menu_items = menu_registry.get_menu_items(context['request'])
    context[var_name] = menu_items
    return ""
