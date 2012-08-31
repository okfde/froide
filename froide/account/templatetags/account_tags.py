from django import template

from froide.account.forms import NewUserForm

register = template.Library()


def get_new_user_form(context, var_name):
    form = NewUserForm()
    context[var_name] = form
    return ""

register.simple_tag(takes_context=True)(get_new_user_form)
